from pulp import LpMaximize, LpProblem, LpVariable, lpSum
from .models import Slate, Game, Team, Player, UserPlayer, CustomUser
import json
import re

def optimize_lineup(player_data, max_total_salary=50000):
    num_players = 8
    position_slots = ['F', 'C', 'G', 'SG', 'PG', 'SF', 'PF', 'UTIL']
    meta_players = {}
    # Separate each player into each position they are eligible for
    for player in player_data:
        meta_player = player.meta_player
        eligible_positions = []
        for position in position_slots:
            if getattr(meta_player, position):
                eligible_positions.append(position)
        player_info = {
            'name': meta_player.name,
            'projection': player.projection,
            'salary': meta_player.salary,
            'positions': eligible_positions
        }
        meta_players[meta_player.name] = player_info
    
    # Create a linear programming problem
    model = LpProblem(name="Optimize_Lineups", sense=LpMaximize)

    # Separate each player into each position they are eligible for
    selected_players = {}
    position_lists = {
        'PG': [],
        'SG': [],
        'SF': [],
        'PF': [],
        'C': [],
        'G': [],
        'F': [],
        'UTIL': []
    }

    for name, meta_player_info in meta_players.items():
        for position in meta_player_info['positions']:
            position_lists[position].append(name)

    # Create binary variables for each player (1 if selected, 0 if not)
    selected_players = {}
    for position, position_list in position_lists.items():
        for player in position_list:
            position_specific_name = f"{player}_{position}"
            selected_players[position_specific_name] = LpVariable(name=position_specific_name, cat='Binary')

    # Objective function: maximize the total projection
    objective_terms = []
    for player_name, player_item in selected_players.items():
        meta_player_name = player_name.split('_')[0]
        objective_terms.append(meta_players[meta_player_name]['projection'] * player_item)
    model += lpSum(objective_terms)


    for position in position_lists:
        # Constraint: select exactly one player per position
        model += lpSum(selected_players[f"{player_name}_{position}"] for player_name in position_lists[position]) == 1

    # Constraint: limit the total salary to max_total_salary
    total_salary_constraint = lpSum(selected_players[player_name] * meta_players[player_name.split('_')[0]]['salary'] for player_name in selected_players) <= max_total_salary
    model += total_salary_constraint

    # Constraint: select exactly num_8 players
    model += lpSum(selected_players[player_name] for player_name in selected_players) == num_players

    # Constraint: Select max one meta player:
    for player_name, player_item in meta_players.items():
        model += lpSum(selected_players[f"{player_name}_{position}"] for position in player_item['positions']) <= 1

    # Solve the problem
    model.solve()

    # Get the selected players
    selected_player_info = {key.split('_')[1]: key.split('_')[0] for key, value in selected_players.items() if value.value() == 1}
    return selected_player_info


def get_lineup_info(optimized_lineup, slate, user=None):
    # Get necessary lineup data
        total_salary = 0
        total_projection = 0
        lineup = {}
        for position, player_name in optimized_lineup.items():
            meta_player_in_lineup = Player.objects.get(name=player_name, slate=slate)
            user_player_in_lineup = UserPlayer.objects.get(meta_player=meta_player_in_lineup, slate=slate, user=user)
            player_in_lineup_info = {}
            player_in_lineup_info['name'] = player_name
            player_in_lineup_info['salary'] = meta_player_in_lineup.salary
            total_salary += meta_player_in_lineup.salary
            player_in_lineup_info['projection'] = user_player_in_lineup.projection
            total_projection += user_player_in_lineup.projection
            player_in_lineup_info['ownership'] = user_player_in_lineup.ownership
            player_in_lineup_info['team'] = meta_player_in_lineup.team.abbrev
            player_in_lineup_info['opponent'] = meta_player_in_lineup.opponent
            lineup[position] = player_in_lineup_info
        lineup['total_salary'] = total_salary
        lineup['total_projection'] = total_projection


def get_slate_info(request, slate_id, user=None):
    try:
        slate = Slate.objects.get(id=slate_id)
        games = Game.objects.filter(slate=slate)
        teams = Team.objects.filter(slate=slate)
        players = Player.objects.filter(slate=slate)
        game_info = []
        for game in games:
            game_info.append(
                {'id': game.id, 'time': game.time, 'home_team': game.home_team.abbrev, 'away_team': game.away_team.abbrev})
        team_info = []
        for team in teams:
            team_info.append({'id': team.id, 'abbrev': team.abbrev})
        player_info = []
        for player in players:
            if user is not None:
                try:
                    user = CustomUser.objects.get(id=request.user.id)
                    user_player = UserPlayer.objects.get(meta_player=player, slate=slate, user=user)
                    projection = user_player.projection
                    ownership = user_player.ownership
                    exposure = user_player.exposure
                except:
                    projection = player.projection
                    ownership = 0
                    exposure = 0
            else:
                projection = player.projection
                ownership = 0
                exposure = 0
            player_info.append({'id': player.id, 'name': player.name,
                                'team': player.team.abbrev, 'salary': player.salary, 'projection': projection, 'dk_id': player.dk_id, 'position': player.position, 'opponent': player.opponent, 'xvalue': '', 'exposure': exposure, 'ownership': ownership})
        slate_info = {'id': slate.id, 'date': slate.date, }
        serialized_data = {
            'slate': slate_info,
            'games': game_info,
            'teams': team_info,
            'players': player_info
        }
        return serialized_data
    except:
        return None
    

def optimize_lineups(request, user=None, numLineups=1):
    # Parse Data
    data = json.loads(request.body)
    slate = Slate.objects.get(id=data['slate-id'])
    user = CustomUser.objects.get(id=data['user-id'])
    player_info = data['players']
    parsed_data = {}
    for key, value in player_info.items():
        match = re.match(r"players\[(\d+)\]\[([a-zA-Z]+)\]", key)
        if match:
            player_id = int(match.group(1))
            attribute = match.group(2)
            if player_id not in parsed_data:
                parsed_data[player_id] = {}
            parsed_data[player_id][attribute] = value
    if user is not None:
        # Update players
        for key, value in parsed_data.items():
            meta_player = Player.objects.get(id=key)
            lock = bool(value['lock'].lower())
            remove = bool(value['remove'].lower())
            exposure = float(value['exposure'])
            ownership = float(value['ownership'])
            projection = (value['projection'])
            player, created = UserPlayer.objects.update_or_create(
                meta_player=meta_player, slate=slate, user=user, defaults={
                    'lock': lock, 'remove': remove, 'exposure': exposure, 'ownership': ownership, 'projection': projection}
            )
        # Gather optomization data
        this_optimization_players = UserPlayer.objects.filter(
            slate=slate, user=user, remove=False)
        optimized_lineup = optimize_lineup(this_optimization_players)
    else:
        # Gather optomization data
        this_optimization_players = Player.objects.filter(
            slate=slate)
        optimized_lineup = optimize_lineup(this_optimization_players)
    lineup = get_lineup_info(optimized_lineup, slate, user)
    return lineup