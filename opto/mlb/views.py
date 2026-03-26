import json
import re
from collections import defaultdict
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Slate, Team, Player, Game, UserOptoSettings, UserPlayer, Optimization, ContestResults
from rest_framework import status
from opto.utils import format_slate
from csv import DictReader
from codecs import iterdecode
from datetime import datetime
from mlb.mlb import get_slate_info, update_default_projections, randomize_within_percentage
from rest_framework.decorators import authentication_classes
from rest_framework.authentication import TokenAuthentication
from fuzzywuzzy import fuzz
from .utils import player_mappings, banned_mappings
import openpyxl
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo


@api_view(['GET'])
def get_slates(request):
    try:
        current_datetime_utc = datetime.now(timezone.utc)
        days_back = request.query_params.get('days_back')
        if days_back:
            cutoff = current_datetime_utc - timedelta(days=int(days_back))
            slates = Slate.objects.filter(
                sport='MLB', date__gte=cutoff).order_by('-date')
        else:
            slate_cutoff = current_datetime_utc.replace(
                hour=6, minute=0, second=0, microsecond=0)
            if current_datetime_utc.hour < 7:
                slate_cutoff -= timedelta(days=1)
            future_slates = Slate.objects.filter(
                sport='MLB', date__gte=slate_cutoff).order_by('date')

            if future_slates.exists():
                slates = future_slates
            else:
                nearest_upcoming_slate = Slate.objects.filter(
                    sport='MLB').order_by('-date').first()
                slates = [nearest_upcoming_slate] if nearest_upcoming_slate else []

        formatted_slates = []
        for slate in slates:
            formatted_slates.append(
                {'id': str(slate.id), 'name': format_slate(slate)})
        return Response(formatted_slates, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
def upload_projections(request):
    method = request.data['method']
    if method != 'file' and method != 'paste':
        return Response({"error": "Invalid method"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        if method == 'file':
            # Get uploaded csv file
            slate_file = request.FILES.get('file')
            if slate_file.name.endswith('.xlsx'):
                # Convert XLSX to CSV
                workbook = openpyxl.load_workbook(slate_file)
                sheet = workbook.active
                csv_text = "\n".join([",".join(map(str, row))
                                     for row in sheet.iter_rows(values_only=True)])
            else:
                # Read as CSV if it's not an XLSX file
                csv_text = slate_file.read().decode('utf-8-sig')
            csv = DictReader(csv_text.splitlines())
        elif method == 'paste':
            paste_projections = request.data['paste-projections']
            projections = json.loads(paste_projections)
        slate = Slate.objects.get(id=int(request.data['slate']))
        user = request.user
        all_players = Player.objects.filter(slate=slate)
        unfound_players = []
        assumed_players = {}
        all_player_data = ''
        if method == 'file':
            all_player_data = csv
        elif method == 'paste':
            all_player_data = projections
            if len(all_player_data) > 1000:
                return Response({"error": "File too large"}, status=status.HTTP_400_BAD_REQUEST)
        # Gather player info
        for row in all_player_data:
            if method == 'file':
                try:
                    player_name = row['Player']
                except:
                    player_name = row['player']
                try:
                    player_projection = float(row['Projection'])
                except:
                    player_projection = float(row['projection'])
            elif method == 'paste':
                player_name = row
                player_projection = float(all_player_data[row])

            try:
                # Perfect Match
                meta_player = Player.objects.get(name=player_name, slate=slate)
                try:
                    # Check if there is already a user player
                    player = UserPlayer.objects.get(
                        slate=slate, user=user, meta_player=meta_player)
                    player.projection = player_projection
                    player.save()
                except:
                    player = UserPlayer.objects.create(
                        slate=slate, user=user, meta_player=meta_player, lock=False, remove=False, ownership=0, exposure=100, projection=player_projection)
                    player.save()
            except:
                player_found = False
                # Check known player mappings
                if player_name in player_mappings:
                    meta_player_name = player_mappings[player_name]
                    try:
                        meta_player = Player.objects.get(
                            name=meta_player_name, slate=slate)
                    except:
                        continue
                    try:
                        # Check if there is already a user player
                        player = UserPlayer.objects.get(
                            slate=slate, user=user, meta_player=meta_player)
                        player.projection = player_projection
                        assumed_players[player_name] = meta_player.name
                        player_found = True
                        player.save()
                        continue
                    except:
                        player = UserPlayer.objects.create(
                            slate=slate, user=user, meta_player=meta_player, lock=False, remove=False, ownership=0, exposure=100, projection=player_projection)
                        assumed_players[player_name] = meta_player.name
                        player_found = True
                        player.save()
                        continue
                for each_player in all_players:
                    # Check un-altered names
                    ratio = fuzz.ratio(each_player.name, player_name)
                    if ratio > 85:
                        # Store sudo match
                        meta_player = each_player
                        if player_name in banned_mappings:
                            if each_player.name == banned_mappings[player_name]:
                                continue
                        try:
                            # Check if there is already a user player
                            player = UserPlayer.objects.get(
                                slate=slate, user=user, meta_player=meta_player)
                            player.projection = player_projection
                            assumed_players[player_name] = meta_player.name
                            player_found = True
                            player.save()
                            break
                        except:
                            player = UserPlayer.objects.create(
                                slate=slate, user=user, meta_player=meta_player, lock=False, remove=False, ownership=0, exposure=100, projection=player_projection)
                            assumed_players[player_name] = meta_player.name
                            player_found = True
                            player.save()
                            break

                    # Check altered names
                    # Alter first name
                    stripped_db_name = ""
                    for ch in each_player.name:
                        if ch.isalpha():
                            stripped_db_name += ch
                    # # Alter second name
                    stripped_csv_name = ""
                    for ch in player_name:
                        if ch.isalpha():
                            stripped_csv_name += ch
                    ratio = fuzz.ratio(stripped_db_name, stripped_csv_name)
                    partial_ratio = fuzz.partial_ratio(stripped_db_name,
                                                       stripped_csv_name)
                    # # Store sudo match
                    if ratio > 75 and partial_ratio > 85:
                        meta_player = each_player
                        if player_name in banned_mappings:
                            if each_player.name == banned_mappings[player_name]:
                                continue
                        try:
                            # Check if there is already a user player
                            player = UserPlayer.objects.get(
                                slate=slate, user=user, meta_player=meta_player)
                            player.projection = player_projection
                            assumed_players[player_name] = meta_player.name
                            player_found = True
                            player.save()
                            break
                        except:
                            player = UserPlayer.objects.create(
                                slate=slate, user=user, meta_player=meta_player, lock=False, remove=False, ownership=0, exposure=100, projection=player_projection)
                            assumed_players[player_name] = meta_player.name
                            player_found = True
                            player.save()
                            break
                if player_found == False:
                    unfound_players.append(player_name)

        return Response({'message': 'Success', "assumed-players": assumed_players, 'unfound-players': unfound_players}, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
def add_slate(request):
    try:
        if request.user.is_staff == False:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        # Get uploaded csv file
        if request.data['projections-only'] == 'true':
            default_projections = request.FILES['file-two']
            slate = Slate.objects.get(pk=int(request.data['slate']))
            update_default_projections(slate.id, default_projections)
            for player in Player.objects.filter(slate=slate):
                new_num = randomize_within_percentage(
                    float(player.projection), 7.5)
                player.projection = new_num
                player.save()
            return Response({})
        try:
            slate_file = request.FILES['file-one']
        except:
            return Response({"error": "No lineup file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            default_projections = request.FILES['file-two']
        except:
            default_projections = None
        csv = DictReader(iterdecode(slate_file, 'utf-8'))
        # Gather slates game info
        game_times = []
        teams = []
        games = []
        for row in csv:
            # Populate game times, teams, and games
            game_info = row['Game Info']
            if game_info == '-' or '@' not in game_info:
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
        EDT = ZoneInfo('America/New_York')  # Avoid naive datetime
        earliest_game = earliest_game.replace(tzinfo=EDT)
        # Create slate
        slate = Slate(date=earliest_game, game_count=game_count, sport='MLB')
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
            game_info = row['Game Info']
            if game_info == '-' or '@' not in game_info:
                # Pass players with no games
                continue
            players_positions = row['Roster Position'].split('/')
            default_position = row['Position']
            position_flags = {'P': False, 'C': False, '1B': False, '2B': False,
                              '3B': False, 'SS': False, 'OF': False}
            for position in players_positions:
                if position in position_flags:
                    position_flags[position] = True
            team = Team.objects.get(abbrev=row['TeamAbbrev'], slate=slate)
            opponent = team.opponent
            projection = 0

            # Add player
            player = Player(name=row['Name'],
                            projection=projection,
                            team=team,
                            opponent=opponent,
                            dk_id=row['ID'],
                            salary=row['Salary'],
                            slate=slate,
                            P=position_flags['P'],
                            C=position_flags['C'],
                            FB=position_flags['1B'],
                            SB=position_flags['2B'],
                            TB=position_flags['3B'],
                            SS=position_flags['SS'],
                            OF=position_flags['OF'],
                            position=default_position)
            player.save()
        # Add default projections
        if default_projections:
            update_default_projections(slate.id, default_projections)
            for player in Player.objects.filter(slate=slate):
                new_num = randomize_within_percentage(
                    float(player.projection), 7.5)
                player.projection = new_num
                player.save()

        return Response({})
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
def remove_projections(request):
    try:
        slate = Slate.objects.get(pk=int(request.data['slate-id']))
        all_players = Player.objects.filter(slate=slate)
        user = request.user
        for player in all_players:
            try:
                player = UserPlayer.objects.get(
                    slate=slate, user=user, meta_player=player)
                if player:
                    player.projection = 0
                    player.save()
            except:
                player = UserPlayer.objects.create(
                    slate=slate, user=user, meta_player=player, lock=False, remove=False, ownership=0, exposure=100, projection=0)
        return Response({'message': 'success'})
    except:
        return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_unauthenticated_slate_info(request, slate_id):
    try:
        slate_info = get_slate_info(request, slate_id)
        return Response({'slate-info': slate_info})
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
def remove_optimizations(request):
    try:
        data = request.body
        data = json.loads(data)
        slate_id = request.data['slate-id']
        slate = Slate.objects.get(pk=int(slate_id))
        user = request.user
        user_optimizations = Optimization.objects.filter(
            user=user, slate=slate)
        for optimization in user_optimizations:
            optimization.delete()
        return Response({'message': 'success'})
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
def get_authenticated_slate_info(request, slate_id):
    try:
        slate_info = get_slate_info(request, slate_id, request.user)
        slate = Slate.objects.get(pk=int(slate_id))
        user_optimizations = Optimization.objects.filter(
            user=request.user, slate=slate)
        optimizations = []
        for optimization in user_optimizations:
            optimizations.append(
                {'id': optimization.id, 'lineups': optimization.lineups, 'exposures': optimization.exposures})
        return Response({'slate-info': slate_info, 'optimizations': optimizations})
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
def player_settings(request):
    try:
        data = request.body
        data = json.loads(data)
        settings = data['settings']
        player_id = data['player']
        meta_player = Player.objects.get(id=player_id)
        slate = meta_player.slate
        user = request.user
        lock = settings['lock']
        remove = settings['remove']
        ownership = settings['ownership']
        exposure = settings['exposure']
        projection = settings['projection']['projection']
        UserPlayer.objects.update_or_create(
            meta_player=meta_player,
            slate=slate,
            user=user,
            defaults={
                'lock': lock,
                'remove': remove,
                'ownership': ownership,
                'exposure': exposure,
                'projection': projection
            }
        )
        return Response({"message": "Player settings updated successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT'])
@authentication_classes([TokenAuthentication])
def user_opto_settings(request):
    try:
        if request.method == 'GET':
            try:
                try:
                    user_opto_settings_object = UserOptoSettings.objects.get(
                        user=request.user)
                except:
                    user_opto_settings_object = UserOptoSettings.objects.create(
                        user=request.user)
                    user_opto_settings_object.save()
                user_opto_settings = {'uniques': user_opto_settings_object.uniques, 'min-salary': user_opto_settings_object.min_salary,
                                      'max-salary': user_opto_settings_object.max_salary, 'max-players-per-team': user_opto_settings_object.max_players_per_team, 'num-lineups': 20, 'hittersVsPitcher': user_opto_settings_object.hittersVsPitcher}
                return Response(user_opto_settings)
            except Exception as e:
                error_message = f"An error occurred: {str(e)}"
                return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif request.method == 'PUT':
            try:
                data = request.body
                data = json.loads(data)
                user_opto_settings_object = UserOptoSettings.objects.get(
                    user=request.user)
                user_opto_settings_object.uniques = data['uniques']
                user_opto_settings_object.min_salary = data['min-salary']
                user_opto_settings_object.max_salary = data['max-salary']
                user_opto_settings_object.max_players_per_team = data['max-players-per-team']
                user_opto_settings_object.hittersVsPitcher = data['hittersVsPitcher']
                user_opto_settings_object.save()
                return Response({"message": "User settings updated successfully"}, status=status.HTTP_200_OK)
            except Exception as e:
                error_message = f"An error occurred: {str(e)}"
                return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
def authenticated_optimize(request):
    try:
        lineups = request.data['lineups']
        slate = request.data['slate']
        slate = Slate.objects.get(pk=int(slate))
        user = request.user
        exposures = request.data['exposures']
        optimization_object = Optimization.objects.create(
            lineups=lineups, exposures=exposures, user=request.user, slate=slate)
        optimization_object.save()
        return Response({'message': 'success'})
    except json.JSONDecodeError as e:
        error_message = f"Invalid JSON data: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
def upload_contest_results(request):
    try:
        slate_id = request.data.get('slate')
        slate_file = request.FILES.get('file')
        if not slate_id or not slate_file:
            return Response({"error": "Missing slate or file"}, status=status.HTTP_400_BAD_REQUEST)

        slate = Slate.objects.get(id=int(slate_id))

        # Build player name -> team abbrev lookup (case-insensitive)
        players_qs = Player.objects.filter(slate=slate).select_related('team')
        player_team_map = {p.name.lower(): p.team.abbrev for p in players_qs}

        slate_file.seek(0)
        csv_text = slate_file.read().decode('utf-8-sig')
        reader = DictReader(csv_text.splitlines())

        # Build case-insensitive column lookup from actual fieldnames
        fieldnames = [f.strip() for f in (reader.fieldnames or [])]
        fieldnames_lower = {f.lower(): f for f in fieldnames}

        def col(row, *candidates):
            for c in candidates:
                key = fieldnames_lower.get(c.lower())
                if key is not None:
                    v = row.get(key)
                    return (v or '').strip()
            return ''

        ownership_data = []
        lineup_entries = []

        for row in reader:
            lineup_str = col(row, 'Lineup')
            rank = col(row, 'Rank')
            if rank and lineup_str:
                try:
                    points = float(col(row, 'Points', 'Score', 'Pts'))
                except (ValueError, AttributeError):
                    points = 0.0
                lineup_entries.append({
                    'lineup_str': lineup_str,
                    'rank': rank,
                    'points': points,
                    'entry_name': col(row, 'EntryName', 'Entry Name', 'Username'),
                })

            player_name = col(row, 'Player', 'Name')
            pct_drafted_raw = col(row, '%Drafted', '%Owned', 'Ownership', 'Owned%')
            fpts_raw = col(row, 'FPTS', 'Fantasy Points', 'Pts', 'Points')
            position = col(row, 'Roster Position', 'Position', 'Pos')
            if player_name:
                try:
                    pct_drafted = float(pct_drafted_raw.rstrip('%').strip())
                except (ValueError, AttributeError):
                    pct_drafted = 0.0
                try:
                    fpts = float(fpts_raw)
                except (ValueError, AttributeError):
                    fpts = 0.0
                ownership_data.append({
                    'name': player_name,
                    'position': position,
                    'pct_drafted': pct_drafted,
                    'fpts': fpts,
                })

        total_entries = len(lineup_entries)

        # Parse lineup strings and compute stacks
        lineup_pattern = re.compile(
            r'(1B|2B|3B|C|OF|P|SS)\s+(.+?)(?=\s+(?:1B|2B|3B|C|OF|P|SS)\s|$)'
        )

        team_stack4 = defaultdict(int)
        team_stack5 = defaultdict(int)
        lineup_details = []

        for entry in lineup_entries:
            lineup_str = entry['lineup_str']
            matches = lineup_pattern.findall(lineup_str)
            players = []
            team_counts = defaultdict(int)
            for pos, name in matches:
                name = name.strip()
                team = player_team_map.get(name.lower())
                players.append({'name': name, 'position': pos, 'team': team})
                if team and pos != 'P':
                    team_counts[team] += 1
            for team, count in team_counts.items():
                if count >= 4:
                    team_stack4[team] += 1
                if count >= 5:
                    team_stack5[team] += 1
            lineup_details.append({
                'players': players,
                'stacked_teams': {t: c for t, c in team_counts.items() if c >= 4},
                'entry_name': entry['entry_name'],
                'rank': entry['rank'],
                'points': entry['points'],
            })

        all_teams = set(team_stack4.keys()) | set(team_stack5.keys())
        stacks = []
        for team in all_teams:
            stacks.append({
                'team': team,
                'stack4_count': team_stack4[team],
                'stack4_pct': round(team_stack4[team] / total_entries * 100, 1) if total_entries else 0,
                'stack5_count': team_stack5[team],
                'stack5_pct': round(team_stack5[team] / total_entries * 100, 1) if total_entries else 0,
            })
        stacks.sort(key=lambda x: x['stack4_count'], reverse=True)

        ContestResults.objects.update_or_create(
            slate=slate,
            defaults={
                'total_entries': total_entries,
                'player_ownership': ownership_data,
                'stacks': stacks,
            }
        )

        return Response({
            'total_entries': total_entries,
            'player_ownership': ownership_data,
            'stacks': stacks,
            'lineup_details': lineup_details,
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_contest_results(request, slate_id):
    try:
        results = ContestResults.objects.get(slate_id=int(slate_id))
        return Response({
            'total_entries': results.total_entries,
            'player_ownership': results.player_ownership,
            'stacks': results.stacks,
        }, status=status.HTTP_200_OK)
    except ContestResults.DoesNotExist:
        return Response(None, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
