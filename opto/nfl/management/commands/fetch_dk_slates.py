import logging
from csv import DictReader
from datetime import datetime

import requests
from django.core.management.base import BaseCommand

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DK_LOBBY_URL = 'https://www.draftkings.com/lobby/getcontests'
DK_CSV_URL = 'https://www.draftkings.com/lineup/getavailableplayerscsv'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

SPORTS = ['NFL', 'NBA', 'MLB']

# CPT (Captain) is the unique showdown position indicator
SHOWDOWN_POSITIONS = {'CPT'}

# Positions expected per sport in a Classic contest
CLASSIC_POSITIONS = {
    'NFL': {'QB', 'RB', 'WR', 'TE', 'DST', 'FLEX'},
    'NBA': {'PG', 'SG', 'SF', 'PF', 'C', 'G', 'F', 'UTIL'},
    'MLB': {'P', 'C', '1B', '2B', '3B', 'SS', 'OF'},
}


class Command(BaseCommand):
    help = 'Fetch DraftKings Classic slates for NFL, NBA, and MLB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sport',
            choices=SPORTS,
            default=None,
            help='Only fetch for a specific sport (default: all)',
        )

    def handle(self, *args, **options):
        sports = [options['sport']] if options['sport'] else SPORTS
        for sport in sports:
            self.stdout.write(f'\n--- {sport} ---')
            try:
                self.process_sport(sport)
            except Exception as e:
                self.stderr.write(f'  ERROR: {e}')
                logger.exception('fetch_dk_slates failed for %s', sport)

    # ------------------------------------------------------------------
    # DraftKings API helpers
    # ------------------------------------------------------------------

    def get_classic_draft_group_ids(self, sport):
        """
        Return all Classic draft group IDs for the given sport.
        Duplicates within the same run are excluded by draft group ID.
        """
        resp = requests.get(
            DK_LOBBY_URL,
            params={'sport': sport},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        classic_type_ids = {
            gt['GameTypeId']
            for gt in data.get('GameTypes', [])
            if gt.get('Name', '').lower() == 'classic'
        }

        if not classic_type_ids:
            return []

        seen = set()
        classic_ids = []
        for dg in data.get('DraftGroups', []):
            if dg.get('GameTypeId') in classic_type_ids:
                dg_id = dg['DraftGroupId']
                if dg_id not in seen:
                    seen.add(dg_id)
                    classic_ids.append(dg_id)

        return classic_ids

    def download_csv(self, draft_group_id):
        resp = requests.get(
            DK_CSV_URL,
            params={'draftGroupId': draft_group_id},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text

    # ------------------------------------------------------------------
    # CSV parsing helpers
    # ------------------------------------------------------------------

    def is_classic_csv(self, csv_text, sport):
        """
        Confirm the CSV is a Classic slate (not Showdown) by checking
        the Roster Position column contains expected Classic positions.
        """
        reader = DictReader(csv_text.splitlines())
        positions_seen = set()
        for row in reader:
            for pos in row.get('Roster Position', '').split('/'):
                positions_seen.add(pos.strip())
        if positions_seen & SHOWDOWN_POSITIONS:
            return False
        if not (positions_seen & CLASSIC_POSITIONS.get(sport, set())):
            return False
        return True

    def parse_game_metadata(self, csv_text):
        """
        Parse game times and teams from the CSV.
        Returns (game_times, teams, games) or raises ValueError if nothing valid.
        """
        reader = DictReader(csv_text.splitlines())
        game_times = []
        teams = []
        games = []
        for row in reader:
            game_info = row.get('Game Info', '')
            if not game_info or game_info == '-' or '@' not in game_info:
                continue
            if game_info not in games:
                games.append(game_info)
            game_teams, game_time = game_info.split(' ', 1)
            away_team, home_team = game_teams.split('@')
            if {'team': away_team, 'opponent': home_team} not in teams:
                teams.append({'team': away_team, 'opponent': home_team})
            if {'team': home_team, 'opponent': away_team} not in teams:
                teams.append({'team': home_team, 'opponent': away_team})
            if game_time not in game_times:
                game_times.append(game_time)
        if not game_times:
            raise ValueError('No valid game info found in CSV')
        return game_times, teams, games

    def parse_earliest_game_dt(self, game_times):
        EDT = ZoneInfo('America/New_York')
        earliest_raw = sorted(game_times)[0][:-3]  # strip timezone suffix
        return datetime.strptime(earliest_raw, '%m/%d/%Y %I:%M%p').replace(tzinfo=EDT)

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------

    def slate_exists(self, sport, earliest_game_dt):
        if sport == 'NFL':
            from nfl.models import Slate
        elif sport == 'NBA':
            from nba.models import Slate
        else:
            from mlb.models import Slate
        return Slate.objects.filter(sport=sport, date=earliest_game_dt).exists()

    # ------------------------------------------------------------------
    # Slate creation
    # ------------------------------------------------------------------

    def create_slate(self, sport, csv_text, game_times, teams, games):
        if sport == 'NFL':
            from nfl.models import Slate, Team, Player, Game
        elif sport == 'NBA':
            from nba.models import Slate, Team, Player, Game
        else:
            from mlb.models import Slate, Team, Player, Game

        EDT = ZoneInfo('America/New_York')
        game_count = len(teams) // 2
        earliest_game = self.parse_earliest_game_dt(game_times)

        slate = Slate.objects.create(
            date=earliest_game,
            game_count=game_count,
            sport=sport,
        )

        for team in teams:
            Team.objects.create(abbrev=team['team'], opponent=team['opponent'], slate=slate)

        for game_info in games:
            game_teams, time_str = game_info.split(' ', 1)
            away_abbrev, home_abbrev = game_teams.split('@')
            home_team_obj = Team.objects.get(abbrev=home_abbrev, slate=slate)
            away_team_obj = Team.objects.get(abbrev=away_abbrev, slate=slate)
            game_time = datetime.strptime(time_str[:-3], '%m/%d/%Y %I:%M%p').replace(tzinfo=EDT)
            Game.objects.create(
                time=game_time,
                home_team=home_team_obj,
                away_team=away_team_obj,
                slate=slate,
            )

        reader = DictReader(csv_text.splitlines())
        for row in reader:
            game_info = row.get('Game Info', '')
            if not game_info or game_info == '-' or '@' not in game_info:
                continue
            team_abbrev = row.get('TeamAbbrev', '')
            if team_abbrev == 'FA':
                continue
            try:
                team_obj = Team.objects.get(abbrev=team_abbrev, slate=slate)
            except Team.DoesNotExist:
                logger.warning('Team not found: %s', team_abbrev)
                continue

            roster_positions = row.get('Roster Position', '').split('/')
            default_position = row.get('Position', '')
            player_kwargs = dict(
                name=row['Name'],
                projection=0,
                team=team_obj,
                opponent=team_obj.opponent,
                dk_id=row['ID'],
                salary=row['Salary'],
                slate=slate,
                position=default_position,
            )

            if sport == 'NFL':
                flags = {p: False for p in ['QB', 'RB', 'WR', 'TE', 'DST', 'FLEX']}
                for pos in roster_positions:
                    if pos in flags:
                        flags[pos] = True
                player_kwargs.update(flags)
            elif sport == 'NBA':
                flags = {p: False for p in ['F', 'C', 'G', 'SG', 'PG', 'SF', 'PF', 'UTIL']}
                for pos in roster_positions:
                    if pos in flags:
                        flags[pos] = True
                player_kwargs.update(flags)
            elif sport == 'MLB':
                flags = {p: False for p in ['P', 'C', '1B', '2B', '3B', 'SS', 'OF']}
                for pos in roster_positions:
                    if pos in flags:
                        flags[pos] = True
                # MLB model uses FB/SB/TB instead of 1B/2B/3B
                player_kwargs.update({
                    'P': flags['P'],
                    'C': flags['C'],
                    'FB': flags['1B'],
                    'SB': flags['2B'],
                    'TB': flags['3B'],
                    'SS': flags['SS'],
                    'OF': flags['OF'],
                })

            Player.objects.create(**player_kwargs)

        return slate

    # ------------------------------------------------------------------
    # Main per-sport flow
    # ------------------------------------------------------------------

    def process_sport(self, sport):
        draft_group_ids = self.get_classic_draft_group_ids(sport)
        if not draft_group_ids:
            self.stdout.write(f'  No Classic contests found')
            return

        self.stdout.write(f'  Found {len(draft_group_ids)} Classic draft group(s): {draft_group_ids}')

        for dg_id in draft_group_ids:
            try:
                csv_text = self.download_csv(dg_id)

                if not self.is_classic_csv(csv_text, sport):
                    self.stdout.write(f'  Draft group {dg_id}: not a Classic slate — skipping')
                    continue

                game_times, teams, games = self.parse_game_metadata(csv_text)
                earliest_game = self.parse_earliest_game_dt(game_times)
                game_count = len(teams) // 2

                if self.slate_exists(sport, earliest_game):
                    self.stdout.write(
                        f'  Draft group {dg_id}: slate already exists for '
                        f'{sport} {earliest_game.date()} ({game_count} games) — skipping'
                    )
                    continue

                slate = self.create_slate(sport, csv_text, game_times, teams, games)
                self.stdout.write(
                    f'  Draft group {dg_id}: created slate #{slate.id} '
                    f'for {sport} {earliest_game.date()} ({game_count} games)'
                )
            except Exception as e:
                self.stderr.write(f'  Draft group {dg_id}: ERROR — {e}')
                logger.exception('Error processing draft group %s for %s', dg_id, sport)
