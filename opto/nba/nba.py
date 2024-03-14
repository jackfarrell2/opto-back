from .models import Slate, Game, Team, Player, UserPlayer, UserOptoSettings
from csv import DictReader
from .utils import player_mappings
from fuzzywuzzy import fuzz
from codecs import iterdecode
import random


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


def update_default_projections(slate, projections):
    # Accept csv
    csv = DictReader(iterdecode(projections, 'utf-8'))
    this_slate = Slate.objects.get(pk=slate)  # Set slate
    all_players = Player.objects.filter(slate=this_slate)
    # Reset projections
    for player in all_players:
        player.projection = 0
        player.save()
    # Pattern match names that don't match
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
            eligible_positions = ['UTIL']
            positions = ['F', 'C', 'G', 'SG', 'PG', 'SF', 'PF']
            for position in positions:
                if getattr(player, position):
                    eligible_positions.append(position)
            if user is not None:
                try:
                    user_player = UserPlayer.objects.get(
                        meta_player=player, slate=slate, user=user)
                    projection = {}
                    projection['projection'] = user_player.projection
                    projection['custom'] = True
                    ownership = user_player.ownership
                    exposure = user_player.exposure
                    remove = user_player.remove
                    lock = user_player.lock
                    if lock:
                        user_locks['count'] += 1
                        user_locks['salary'] += player.salary

                except:
                    projection = {
                        'projection': player.projection, 'custom': False}
                    ownership = 0
                    exposure = 100
                    remove = False
                    lock = False
            else:
                projection = {'projection': player.projection, 'custom': False}
                ownership = 0
                exposure = 100
                remove = False
                lock = False

            player_info.append({'id': str(player.id), 'name': player.name,
                                'team': player.team.abbrev, 'salary': player.salary, 'projection': projection, 'remove': remove, 'lock': lock, 'dk_id': player.dk_id, 'position': player.position, 'opponent': player.opponent, 'xvalue': '', 'exposure': exposure, 'ownership': ownership, 'eligiblePositions': eligible_positions
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
