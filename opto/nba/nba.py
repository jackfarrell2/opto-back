from pulp import LpMaximize, LpProblem, LpVariable, lpSum
from .models import Slate, Game, Team, Player, UserPlayer, UserOptoSettings
import re
import json
from csv import DictReader
from .utils import player_mappings
from fuzzywuzzy import fuzz
from codecs import iterdecode
import random
import math
from collections import OrderedDict


def store_opto_settings(user, slate, settings):
    UserOptoSettings.objects.update_or_create(
        user=user, defaults={
            'uniques': settings['uniques'],
            'max_salary': settings['maxSalary'],
            'min_salary': settings['minSalary'],
            'max_players_per_team': settings['maxTeamPlayers']
        }
    )


def randomize_within_percentage(number, percentage):
    if percentage < 0 or percentage > 100:
        raise ValueError("Percentage must be between 0 and 100")

    deviation = (percentage / 100) * number
    lower_bound = number - deviation
    upper_bound = number + deviation

    randomized_number = random.uniform(lower_bound, upper_bound)
    return randomized_number


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
    removed_players = []
    locks = []
    teams = Team.objects.filter(slate=slate)
    team_list = {}
    for i in range(len(teams)):
        this_team_list = []
        team = teams[i]
        team_players = Player.objects.filter(slate=slate, team=team)
        for player in team_players:
            this_team_list.append(player.id)
        team_list[team.abbrev] = this_team_list
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
        else:
            removed_players.append(str(meta_player.id))
    return {'slate': slate, 'players': this_optimization_players, 'opto-settings': data['opto-settings'], 'locks': locks, 'teams': team_list, 'removed-players': removed_players}


def optimize(players, settings, teams):
    # User Settings
    lineups = []
    opto_lineups = []
    slate = settings['slate']
    uniques = int(settings['uniques'])
    max_team_players = int(settings['maxTeamPlayers'])
    min_team_salary = int(settings['minSalary'])
    max_team_salary = int(settings['maxSalary'])
    removed_players = settings['removed-players']
    locks = settings['locks']
    # To be updated later
    num_lineups = int(settings['numLineups'])
    # Global Settings
    num_players = 8
    position_slots = ['F', 'C', 'G', 'SG', 'PG', 'SF', 'PF', 'UTIL']
    meta_players = {}
    locked_players = {}
    exposure_tracker = {}
    general_count_tracker = {}
    # Separate each player into each position they are eligible for
    for player, players_optimization_info in players.items():
        if players_optimization_info['exposure'] < 100:
            exposure_tracker[player] = {
                'count': 0, 'exposure': players_optimization_info['exposure']}
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
                       for position in player_item['positions']) <= 1, f"max_one_{player_id}"

    # Constraint: Limit the number of players from each team
    for team, team_players in teams.items():
        team_players_per_position = []
        for team_player in team_players:
            if str(team_player) not in removed_players:
                for position in meta_players[str(team_player)]['positions']:
                    team_players_per_position.append(
                        selected_players[f"{team_player}_{position}"])
        model += lpSum(team_players_per_position) <= max_team_players

    # Build lineups
    overexposed_players = []
    opto_count = 0
    for i in range(num_lineups):
        # Constraint - check if a player is overexposed
        for player in overexposed_players[:]:
            players_current_exposure = (
                exposure_tracker[player]['count'] / opto_count) * 100
            if players_current_exposure <= exposure_tracker[player]['exposure']:
                overexposed_players.remove(player)
                model.constraints.pop(f"overexposed_{player}")
        for overexposed_player in overexposed_players:
            overexposed_player_constraint_name = f"overexposed_{overexposed_player}"
            if overexposed_player_constraint_name not in model.constraints:
                players_positions_variables = []
                for position in meta_players[overexposed_player]['positions']:
                    players_positions_variables.append(
                        selected_players[f"{overexposed_player}_{position}"])
                players_constraint = lpSum(players_positions_variables) == 0
                model += players_constraint, f"overexposed_{overexposed_player}"

        # Constraint - add previous lineup uniqueness
        previous_lineup = opto_lineups[i-1] if i > 0 else None
        if previous_lineup:
            all_player_versions = []
            for player, player_id in previous_lineup.items():
                for position in meta_players[player_id]['positions']:
                    all_player_versions.append(
                        selected_players[f"{player_id}_{position}"])
            model += lpSum(all_player_versions) <= (num_players - uniques)
        opto_count += 1
        # Solve the problem
        model.solve()
        # Get the selected players
        these_selected_players = {key.split('_')[1]: key.split(
            '_')[0] for key, value in selected_players.items() if value.value() == 1}
        lineup_info = get_lineup_info(these_selected_players, players, general_count_tracker)
        general_count_tracker = lineup_info['general-count-tracker']
        opto_lineups.append(these_selected_players)
        # Check for overexposed players
        for exposure_player in these_selected_players.values():
            if exposure_player in exposure_tracker:
                exposure_tracker[exposure_player]['count'] += 1
                current_exposure = (
                    exposure_tracker[exposure_player]['count'] / opto_count) * 100
                if current_exposure > exposure_tracker[exposure_player]['exposure']:
                    overexposed_players.append(exposure_player)
        lineups.append(lineup_info['lineup-info'])

    exposures = {}
    for exposure_id, exposure_info in general_count_tracker.items():
        exposures[exposure_id] = {'exposure': math.floor(((exposure_info['count'] / num_lineups) * 100)), 'player-name': exposure_info['name'], 'team': exposure_info['team'], 'count': exposure_info['count']}
    return {'lineups': lineups, 'exposures': exposures, 'complete': True}


def get_lineup_info(selected_players, player_data, general_count_tracker):
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
        player_in_lineup_info['dk-id'] = meta_player_in_lineup.dk_id
        if str(meta_player_in_lineup.dk_id) in general_count_tracker:
            general_count_tracker[str(meta_player_in_lineup.dk_id)]['count'] += 1
        else:
            general_count_tracker[str(meta_player_in_lineup.dk_id)] = {'count': 1, 'name': meta_player_in_lineup.name, 'team': meta_player_in_lineup.team.abbrev}
        lineup[position] = player_in_lineup_info
    lineup['total_salary'] = total_salary
    lineup['total_projection'] = round(total_projection, 2)
    return {'lineup-info': lineup, 'general-count-tracker': general_count_tracker}


def update_default_projections(slate, projections):
    # Accept csv
    csv = DictReader(iterdecode(projections, 'utf-8'))
    this_slate = Slate.objects.get(pk=slate)  # Set slate
    # Pattern match names that don't match
    all_players = Player.objects.filter(slate=this_slate)
    for row in csv:
        player_name = row['Player']
        try:
            # Check if there is a perfect match
            player = Player.objects.get(name=player_name, slate=this_slate)
        except:
            # Check if there is a sudo-match
            # Check known player mappings
            if player_name in player_mappings:
                meta_player_name = player_mappings[player_name]
                try:
                    player = Player.objects.get(
                        name=meta_player_name, slate=slate)
                except:
                    continue
            for each_player in all_players:
                # Check un-altered names
                ratio = fuzz.ratio(each_player.name, player_name)
                if ratio > 85:
                    # Store sudo match
                    player = each_player
                    player.projection = row['Proj']
                    player.save()
                    break
                # Check altered names
                # Alter first name
                stripped_db_name = ""
                for ch in each_player.name:
                    if ch.isalpha():
                        stripped_db_name += ch
                # Alter second name
                stripped_csv_name = ""
                for ch in player_name:
                    if ch.isalpha():
                        stripped_csv_name += ch
                ratio = fuzz.ratio(stripped_db_name, stripped_csv_name)
                partial_ratio = fuzz.partial_ratio(stripped_db_name,
                                                   stripped_csv_name)
                # Store sudo match
                if ratio > 75 and partial_ratio > 85:
                    player = each_player
                    player.projection = row['Proj']
                    player.save()
                    break
            continue
        # Store perfect match
        player.projection = row['Proj']
        player.save()
    return True


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
