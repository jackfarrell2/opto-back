import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Slate, Team, Player, Game, UserOptoSettings
from rest_framework import status
from opto.utils import format_slate
from csv import DictReader
from codecs import iterdecode
from backports.zoneinfo import ZoneInfo
from datetime import datetime
from django.core.serializers.json import DjangoJSONEncoder
from decimal import Decimal
from django.http import JsonResponse
from nba.nba import prepare_optimize, get_slate_info, optimize
from rest_framework.decorators import authentication_classes
from rest_framework.authentication import TokenAuthentication


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
def get_unauthenticated_slate_info(request, slate_id):
    try:
        slate_info = get_slate_info(request, slate_id)
        return Response(slate_info)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
def get_authenticated_slate_info(request, slate_id):
    try:
        slate_info = get_slate_info(request, slate_id, request.user)
        return Response(slate_info)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
def get_user_opto_settings(request):
    try:
        try:
            user_opto_settings_object = UserOptoSettings.objects.get(user=request.user)
        except:
            user_opto_settings_object = UserOptoSettings.objects.create(user=request.user)
            user_opto_settings_object.save()
        user_opto_settings = {'max-salary': user_opto_settings_object.max_salary, 'min-salary': user_opto_settings_object.min_salary, 'max-players-per-team': user_opto_settings_object.max_players_per_team, 'uniques': user_opto_settings_object.uniques}
        return Response(user_opto_settings)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
def update_uniques(request):
    try:
        data = request.body
    except Exception as e:
        error_message = f"Invalid JSON data: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
def authenticated_optimize(request):
    try:
        optimization_info = prepare_optimize(request, request.user)
        player_data = optimization_info['players']
        opto_settings = optimization_info['opto-settings']
        opto_settings['slate'] = optimization_info['slate']
        opto_settings['locks'] = optimization_info['locks']
        lineups = optimize(player_data, opto_settings)
        return JsonResponse({'lineups': lineups}, status=status.HTTP_200_OK, encoder=DecimalEncoder)
    except json.JSONDecodeError as e:
        error_message = f"Invalid JSON data: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
def unauthenticated_optimize(request):
    try:
        optimization_info = prepare_optimize(request)
        player_data = optimization_info['players']
        opto_settings = optimization_info['opto-settings']
        opto_settings['slate'] = optimization_info['slate']
        opto_settings['locks'] = optimization_info['locks']
        lineups = optimize(player_data, opto_settings)
        return JsonResponse({'lineups': lineups}, status=status.HTTP_200_OK, encoder=DecimalEncoder)
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