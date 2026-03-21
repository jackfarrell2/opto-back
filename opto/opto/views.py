import os

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from nfl.management.commands.fetch_dk_slates import Command as FetchCommand

INGEST_SECRET = os.environ.get('DK_INGEST_SECRET', '')
VALID_SPORTS = {'NFL', 'NBA', 'MLB'}


@api_view(['POST'])
def ingest_dk_slate(request):
    secret = request.headers.get('X-Ingest-Key', '')
    if not INGEST_SECRET or secret != INGEST_SECRET:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    sport = request.data.get('sport')
    csv_text = request.data.get('csv')

    if sport not in VALID_SPORTS:
        return Response({'error': 'Invalid sport'}, status=status.HTTP_400_BAD_REQUEST)
    if not csv_text:
        return Response({'error': 'Missing csv'}, status=status.HTTP_400_BAD_REQUEST)

    cmd = FetchCommand()

    if not cmd.is_classic_csv(csv_text, sport):
        return Response({'skipped': True, 'reason': 'not a classic slate'})

    try:
        game_times, teams, games = cmd.parse_game_metadata(csv_text)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    earliest_game = cmd.parse_earliest_game_dt(game_times)

    if cmd.slate_exists(sport, earliest_game):
        return Response({'skipped': True, 'reason': 'slate already exists'})

    slate = cmd.create_slate(sport, csv_text, game_times, teams, games)
    return Response({'created': True, 'slate_id': slate.id})
