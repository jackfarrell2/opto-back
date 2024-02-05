from pulp import LpMaximize, LpProblem, LpVariable, lpSum
from .models import Slate, Game, Team, Player, UserPlayer, UserOptoSettings
import re
import json


def store_opto_settings(user, slate, settings):
    UserOptoSettings.objects.update_or_create(
        user=user, defaults={
            'uniques': settings['uniques'],
            'max_salary': settings['maxSalary'],
            'min_salary': settings['minSalary'],
            'max_players_per_team': settings['maxTeamPlayers']
        }
    )


def prepare_optimize(request, user=None):
    # Parse Data
    data = json.loads(request.body)
    slate = Slate.objects.get(id=data['slate-id'])
    player_info = data['players']
    # Store opto info
    if user is not None:
        store_opto_settings(user, slate, data['opto-settings'])
    parsed_data = {}
    for key, value in player_info.items():
        match = re.match(r"players\[(\d+)\]\[([a-zA-Z]+)\]", key)
        if match:
            player_id = int(match.group(1))
            attribute = match.group(2)
            if player_id not in parsed_data:
                parsed_data[player_id] = {}
            parsed_data[player_id][attribute] = value
    this_optimization_players = {}
    locks = []
    for key, value in parsed_data.items():
        meta_player = Player.objects.get(id=key)
        lock = bool(value['lock'].lower())
        if lock:
            locks.append(str(meta_player.id))
        remove = bool(value['remove'].lower())
        exposure = float(value['exposure'])
        ownership = float(value['ownership'])
        projection = float(value['projection'])
        # Store user info
        if user is not None:
            player, created = UserPlayer.objects.update_or_create(
                meta_player=meta_player, slate=slate, user=user, defaults={
                    'lock': lock, 'remove': remove, 'exposure': exposure, 'ownership': ownership, 'projection': projection}
            )
        if not remove:
            this_optimization_players[str(meta_player.id)] = {
                'name': meta_player.name, 'lock': lock, 'remove': remove, 'exposure': exposure, 'ownership': ownership, 'projection': projection}
    return {'slate': slate, 'players': this_optimization_players, 'opto-settings': data['opto-settings'], 'locks': locks}


def optimize(players, settings):
    # User Settings
    lineups = []
    slate = settings['slate']
    # num_lineups = settings['num-lineups']
    uniques = int(settings['uniques'])
    max_team_players = int(settings['maxTeamPlayers'])
    min_team_salary = int(settings['minSalary'])
    max_team_salary = int(settings['maxSalary'])
    locks = settings['locks']
    # To be updated later
    num_lineups = 1
    # Global Settings
    num_players = 8
    position_slots = ['F', 'C', 'G', 'SG', 'PG', 'SF', 'PF', 'UTIL']
    meta_players = {}
    locked_players = {}
    # Separate each player into each position they are eligible for
    for player, players_optimization_info in players.items():
        meta_player = Player.objects.get(id=int(player))
        eligible_positions = []
        for position in position_slots:
            if getattr(meta_player, position):
                eligible_positions.append(position)
        if player in locks:
            locked_players[player] = eligible_positions
        player_info = {
            'name': players_optimization_info['name'],
            'projection': players_optimization_info['projection'],
            'salary': meta_player.salary,
            'positions': eligible_positions
        }
        meta_players[str(meta_player.id)] = player_info

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

    for meta_player_id, meta_player_info in meta_players.items():
        for position in meta_player_info['positions']:
            position_lists[position].append(meta_player_id)

    # Create binary variables for each player (1 if selected, 0 if not)
    selected_players = {}
    for position, position_list in position_lists.items():
        for player in position_list:
            position_specific_name = f"{player}_{position}"
            selected_players[position_specific_name] = LpVariable(
                name=position_specific_name, cat='Binary')

    # Objective function: maximize the total projection
    objective_terms = []
    for player_id, player_item in selected_players.items():
        player_id = player_id.split('_')[0]
        objective_terms.append(
            meta_players[player_id]['projection'] * player_item)
    model += lpSum(objective_terms)

    # Constraint: select exactly one player per position
    for position in position_lists:
        model += lpSum(selected_players[f"{player_id}_{position}"]
                       for player_id in position_lists[position]) == 1

    # Constraint: lock players
    for lock_id, position in locked_players.items():
        model += lpSum(selected_players[f"{lock_id}_{position}"]
                       for position in position) == 1

    # Constraint: limit the total salary to max_total_salary
    total_salary_constraint_max = lpSum(selected_players[player_id] * meta_players[player_id.split(
        '_')[0]]['salary'] for player_id in selected_players) <= max_team_salary
    model += total_salary_constraint_max

    # Constraint: limit the total salary to min_team_salary
    total_salary_constraint_min = lpSum(selected_players[player_id] * meta_players[player_id.split(
        '_')[0]]['salary'] for player_id in selected_players) >= min_team_salary
    model += total_salary_constraint_min

    # Constraint: select exactly num_8 players
    model += lpSum(selected_players[player_id]
                   for player_id in selected_players) == num_players

    # Constraint: Select max one meta player:
    for player_id, player_item in meta_players.items():
        model += lpSum(selected_players[f"{player_id}_{position}"]
                       for position in player_item['positions']) <= 1

    for i in range(num_lineups):
        # Solve the problem
        model.solve()
        # Get the selected players
        selected_players = {key.split('_')[1]: key.split(
            '_')[0] for key, value in selected_players.items() if value.value() == 1}
        lineup_info = get_lineup_info(selected_players, players)
        lineups.append(lineup_info)

    return lineups


def get_lineup_info(selected_players, player_data):
    # Get necessary lineup data
    total_salary = 0
    total_projection = 0
    lineup = {}
    for position, player_id in selected_players.items():
        meta_player_in_lineup = Player.objects.get(id=player_id)
        user_player_info = player_data[player_id]
        player_in_lineup_info = {}
        player_in_lineup_info['name'] = meta_player_in_lineup.name
        player_in_lineup_info['salary'] = meta_player_in_lineup.salary
        total_salary += meta_player_in_lineup.salary
        player_in_lineup_info['projection'] = user_player_info['projection']
        total_projection += user_player_info['projection']
        player_in_lineup_info['ownership'] = user_player_info['ownership']
        player_in_lineup_info['team'] = meta_player_in_lineup.team.abbrev
        player_in_lineup_info['opponent'] = meta_player_in_lineup.opponent
        lineup[position] = player_in_lineup_info
    lineup['total_salary'] = total_salary
    lineup['total_projection'] = round(total_projection, 2)
    return lineup


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
        user_locks = {'count': 0, 'salary': 0}
        for player in players:
            if user is not None:
                try:
                    user_player = UserPlayer.objects.get(
                        meta_player=player, slate=slate, user=user)
                    projection = {}
                    projection['projection'] = user_player.projection
                    projection['custom'] = False
                    ownership = user_player.ownership
                    exposure = user_player.exposure
                    remove = user_player.remove
                    lock = user_player.lock
                    if lock:
                        user_locks['count'] += 1
                        user_locks['salary'] += player.salary
                    if user_player.projection != player.projection:
                        projection['custom'] = True

                except:
                    projection = {
                        'projection': player.projection, 'custom': False}
                    ownership = 0
                    exposure = 0
                    remove = False
                    lock = False
            else:
                projection = {'projection': player.projection, 'custom': False}
                ownership = 0
                exposure = 0
                remove = False
                lock = False
            player_info.append({'id': player.id, 'name': player.name,
                                'team': player.team.abbrev, 'salary': player.salary, 'projection': projection, 'remove': remove, 'lock': lock, 'dk_id': player.dk_id, 'position': player.position, 'opponent': player.opponent, 'xvalue': '', 'exposure': exposure, 'ownership': ownership,
                                })
        slate_info = {'id': slate.id, 'date': slate.date, }
        serialized_data = {
            'slate': slate_info,
            'games': game_info,
            'teams': team_info,
            'players': player_info,
            'user-locks': user_locks,
        }
        return serialized_data
    except:
        return None
