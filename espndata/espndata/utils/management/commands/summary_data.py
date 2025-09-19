from django.conf import settings
from django.core.management.base import BaseCommand

from dateutil import parser as dateparser
import json
import logging
import requests
import time
from tqdm import tqdm

from espndata.eventdata.models import Event
from espndata.utils import convert_to_decimal

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

class Command(BaseCommand):
    help = 'Uses stored ESPN event IDs to collect and parse ESPN event summaries.'

    def handle(self, *args, **options):
        league_sport_map = {
            'college-football': 'football',
            'nfl': 'football',
            'nba': 'basketball',
            'mlb': 'baseball',
        }
        incomplete_event_data = {
            'college-football': set(),
            'nfl': set(),
            'nba': set(),
            'mlb': set(),
        }
        base_espn_api_url = 'https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary'
        ids_file_path = settings.BASE_DIR / 'espndata' / '_raw_data' / 'all_event_ids.json'
        
        with open(ids_file_path, 'r') as ids_file:
            ids_by_league = json.load(ids_file)

        # total_games = sum([len(league_ids) for league_ids in ids_by_league.values()])
        total_games = 4
        new_events = []

        with tqdm(total=total_games, desc='Fetching and Parsing event summaries') as prog_bar:
            for league, ids_list in ids_by_league.items():
                sport = league_sport_map[league]
                formatted_url = base_espn_api_url.format(sport=sport, league=league)
                ids_list = [ids_list[798]]
                
                for espn_id in ids_list:
                    params = {'event': espn_id}
                    event_summary = self.request_with_retry(formatted_url, params).json()

                    header_info = event_summary.get('header', {})
                    season_info = header_info.get('season')
                    if not season_info:
                        incomplete_event_data[league].add(espn_id)
                        continue
                    
                    season_type = season_info.get('type')
                    if season_type == 1:
                        continue        # ignore pre-season events
                    
                    season_year = season_info.get('year')
                    week = header_info.get('week')

                    comp = next(iter(header_info.get('competitions', [])))
                    if not comp:
                        incomplete_event_data[league].add(espn_id)
                        continue
                    
                    event_status = comp.get('status', {}).get('type', {}).get('id')
                    if event_status == '5' or event_status == '6':
                        continue        # ignore postponed or cancelled events
                    
                    event_date = comp.get('date')
                    event_date = dateparser.parse(event_date)

                    teams = comp.get('competitors', [])
                    home = next((t for t in teams if t.get('homeAway') == 'home'), None)
                    away = next((t for t in teams if t.get('homeAway') == 'away'), None)
                    if not (home and away):
                        incomplete_event_data[league].add(espn_id)
                        continue
                    
                    home_team = home.get('team', {}).get('displayName')
                    home_rank = home.get('rank')
                    is_home_win = home.get('winner', False)
                    away_team = away.get('team', {}).get('displayName')
                    away_rank = away.get('rank')
                    is_away_win = away.get('winner', False)
                    both_ranked_matchup = bool(home_rank and away_rank)
                    one_ranked_matchup = bool(home_rank) != bool(away_rank)
                    neutral_site = comp.get('neutralSite', False)

                    win_probs = event_summary.get('winprobability', [])
                    pre_win_probs = next(iter(win_probs), {})
                    if not pre_win_probs:
                        incomplete_event_data[league].add(espn_id)
                        continue
                    
                    home_win_prob = pre_win_probs.get('homeWinPercentage') * 100
                    away_win_prob = 100 - home_win_prob

                    betting_data = next(iter(event_summary.get('pickcenter', [])), {})
                    home_american_ml = betting_data.get('homeTeamOdds', {}).get('moneyLine')
                    home_decimal_ml = convert_to_decimal(home_american_ml)
                    away_american_ml = betting_data.get('awayTeamOdds', {}).get('moneyLine')
                    away_decimal_ml = convert_to_decimal(away_american_ml)

                    event = Event(
                        league=league,
                        espn_id=espn_id,
                        date=event_date,
                        season=season_year,
                        week=week,
                        season_type=season_type,
                        home_team=home_team,
                        home_rank=home_rank,
                        home_win_probability=home_win_prob,
                        home_moneyline=home_decimal_ml,
                        is_home_win=is_home_win,
                        away_team=away_team,
                        away_rank=away_rank,
                        away_win_probability=away_win_prob,
                        away_moneyline=away_decimal_ml,
                        is_away_win=is_away_win,
                        is_neutral_site=neutral_site,
                        both_ranked_matchup=both_ranked_matchup,
                        one_ranked_matchup=one_ranked_matchup,
                    )
                    new_events.append(event)

        Event.objects.bulk_create(new_events)

        # write list of incomplete data events to a file
        # clear current all_event_ids json for future use
    
    def request_with_retry(self, url, params):
        """ 
        Executes the HTTP request and returns the response.
        Built in retries. Raises RunTimeError if unsuccessful after {max_retries} attempts.
        """
        max_retries = 5
        backoff = 1.0
        headers = {
            'Accept': 'application/xml; charset=utf-8',
            'User-Agent': 'foo',
        }

        for attempt in range(max_retries):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                resp.raise_for_status()
                return resp
            except Exception as e:
                logging.warning(f'Request failed {url}. Attempt {attempt + 1}/{max_retries}. Error: {e}')
                time.sleep(backoff * (5 ** attempt))
        
        raise RuntimeError(f'Failed to fetch {url} after {max_retries} attempts')