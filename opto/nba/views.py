import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Slate, Team, Player, Game, UserPlayer
from rest_framework import status
from opto.utils import format_slate
from csv import DictReader
from codecs import iterdecode
from backports.zoneinfo import ZoneInfo
from datetime import datetime
import re
from django.core.serializers.json import DjangoJSONEncoder
from decimal import Decimal
from users.models import CustomUser
from django.http import JsonResponse
from nba.nba import optimize_lineup


@api_view(['GET'])
def get_slates(request):
    try:
        slates = Slate.objects.filter(sport='NBA').order_by('date')
        formatted_slates = []
        for slate in slates:
            formatted_slates.append(
                {'id': str(slate.id), 'name': format_slate(slate)})
        return Response(formatted_slates, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def add_slate(request):
    # Get uploaded csv file
    slate_file = request.FILES['file']
    csv = DictReader(iterdecode(slate_file, 'utf-8'))
    # Gather slates game info
    game_times = []
    teams = []
    games = []
    for row in csv:
        # Populate game times, teams, and games
        game_info = row['Game Info']
        if game_info == '-':
            # Pass players with no games
            continue
        if game_info not in games:
            games.append(game_info)  # Add game
        game_teams, game_time = game_info.split(" ", 1)
        away_team, home_team = game_teams.split('@')
        # Add teams
        if ({'team': away_team, 'opponent': home_team}) not in teams:
            teams.append({'team': away_team, 'opponent': home_team})
        if ({'team': home_team, 'opponent': away_team}) not in teams:
            teams.append({'team': home_team, 'opponent': away_team})
        # Add game times
        if game_time not in game_times:
            game_times.append(game_time)
    game_count = int(len(teams) / 2)  # Game Count
    # Store slate time
    earliest_game = sorted(game_times)[0]
    earliest_game = earliest_game[:-3]  # Strip time zone
    earliest_game = datetime.strptime(earliest_game, '%m/%d/%Y %I:%M%p')
    EDT = ZoneInfo('US/Eastern')  # Avoid naive datetime
    earliest_game = earliest_game.replace(tzinfo=EDT)
    # Create slate
    slate = Slate(date=earliest_game, game_count=game_count, sport='NBA')
    slate.save()
    # Create teams for the slate
    for team in teams:
        # Add teams
        this_team = Team.objects.create(
            abbrev=team['team'], opponent=team['opponent'], slate=slate)
        this_team.save()
    for game in games:
        # Add games
        teams, time = game.split(' ', 1)
        # Add home and away teams
        away_team, home_team = teams.split('@')
        home_team = Team.objects.get(abbrev=home_team, slate=slate)
        away_team = Team.objects.get(abbrev=away_team, slate=slate)
        # Add game time
        time = time[:-3]
        time = datetime.strptime(time, '%m/%d/%Y %I:%M%p')
        time = earliest_game.replace(tzinfo=EDT)  # Avoid naive datetime
        this_game = Game.objects.create(time=time, home_team=home_team,
                                        away_team=away_team, slate=slate)
        this_game.save()
    # Save players and positions
    csv = DictReader(iterdecode(slate_file, 'utf-8'))
    for row in csv:
        players_positions = row['Roster Position'].split('/')
        default_position = row['Position']
        position_flags = {'F': False, 'C': False, 'G': False, 'SG': False,
                          'PG': False, 'SF': False, 'PF': False, 'UTIL': False}
        for position in players_positions:
            if position in position_flags:
                position_flags[position] = True
        team = Team.objects.get(abbrev=row['TeamAbbrev'], slate=slate)
        opponent = team.opponent
        projection = row['AvgPointsPerGame']

        # Add player
        player = Player(name=row['Name'],
                        projection=projection,
                        team=team,
                        opponent=opponent,
                        dk_id=row['ID'],
                        salary=row['Salary'],
                        slate=slate,
                        F=position_flags['F'],
                        C=position_flags['C'],
                        G=position_flags['G'],
                        SG=position_flags['SG'],
                        PG=position_flags['PG'],
                        SF=position_flags['SF'],
                        PF=position_flags['PF'],
                        UTIL=position_flags['UTIL'],
                        position=default_position)
        player.save()
    return Response({})


@api_view(['GET'])
def get_slate(request, slate_id):
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
            player_info.append({'id': player.id, 'name': player.name,
                                'team': player.team.abbrev, 'salary': player.salary, 'projection': player.projection, 'dk_id': player.dk_id, 'position': player.position, 'opponent': player.opponent, 'xvalue': '', 'exposure': '0', 'ownership': '0'})
        slate_info = {'id': slate.id, 'date': slate.date, }
        serialized_data = {
            'slate': slate_info,
            'games': game_info,
            'teams': team_info,
            'players': player_info
        }
        return Response(serialized_data)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def optimize(request):
    try:
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
        # Calc total salary
        lineup['total_salary'] = total_salary
        lineup['total_projection'] = total_projection
        return JsonResponse({'lineup': lineup}, status=status.HTTP_200_OK, encoder=DecimalEncoder)
    except json.JSONDecodeError as e:
        error_message = f"Invalid JSON data: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DecimalEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)