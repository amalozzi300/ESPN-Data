from django.conf import settings
from django.core.management.base import BaseCommand

import json
import logging
import requests
import time

from espndata.utils import convert_to_decimal

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

class Command(BaseCommand):
    help = 'Uses stored ESPN event IDs to collect and parse ESPN event summaries.'

    def handle(self, *args, **otpions):
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

        for league, ids_list in ids_by_league.items():
            sport = league_sport_map[league]
            formatted_url = base_espn_api_url.format(sport=sport, league=league)
            
            event_id = ids_list[671]
            


            params = {'event': event_id}
            event_summary = self.request_with_retry(formatted_url, params).json()

            header_info = event_summary.get('header')
            if not header_info:
                incomplete_event_data[league].add(event_id)
                continue
            comp = next(iter(header_info.get('competitions', [])))
            if not comp:
                incomplete_event_data[league].add(event_id)
                continue
            
            event_status = comp.get('status', {}).get('type', {}).get('id')
            if event_status == '5' or event_status == '6':
                continue
            
            event_date = comp.get('date')

            season_info = header_info.get('season')
            if not season_info:
                incomplete_event_data[league].add(event_id)
                continue
            season_year = season_info.get('year')
            season_type = season_info.get('type')
            week = header_info.get('week')

            teams = comp.get('competitors', [])
            home = next((t for t in teams if t.get('homeAway') == 'home'), None)
            away = next((t for t in teams if t.get('homeAway') == 'away'), None)
            if not (home and away):
                incomplete_event_data[league].add(event_id)
                continue
            home_team = home.get('team', {}).get('displayName')
            away_team = away.get('team', {}).get('displayName')
            home_rank = home.get('rank')
            away_rank = away.get('rank')
            ranked_matchup = bool(home_rank and away_rank)
            one_ranked = bool(home_rank) != bool(away_rank)
            home_winner = home.get('winner', False)
            away_winner = away.get('winner', False)

            neutral_site = comp.get('neutralSite', False)

            win_probs = event_summary.get('winprobability', [])
            pre_win_probs = next(iter(win_probs), {})
            if not pre_win_probs:
                incomplete_event_data[league].add(event_id)
                continue
            home_win_prob = pre_win_probs.get('homeWinPercentage') * 100
            away_win_prob = 100 - home_win_prob

            betting_data = next(iter(event_summary.get('pickcenter', [])), {})
            home_american_ml = betting_data.get('homeTeamOdds', {}).get('moneyLine')
            away_american_ml = betting_data.get('awayTeamOdds', {}).get('moneyLine')
            home_decimal_ml = convert_to_decimal(home_american_ml)
            away_decimal_ml = convert_to_decimal(away_american_ml)

            print(f'League: {league}')
            print(f'ESPN ID: {event_id}')
            print(f'Date: {event_date}')
            print(f'Season Year: {season_year}')
            print(f'Week Number: {week}')
            print(f'Season Type: {season_type}')
            print(f'Home Team: {home_team}')
            print(f'Home Rank: {home_rank}')
            print(f'Home Win %: {home_win_prob}')
            print(f'Home American ML: {home_american_ml}')
            print(f'Home Decimal ML: {home_decimal_ml}')
            print(f'Home Win: {home_winner}')
            print(f'Away Team: {away_team}')
            print(f'Away Rank: {away_rank}')
            print(f'Away Win %: {away_win_prob}')
            print(f'Away American ML: {away_american_ml}')
            print(f'Away Decimal ML: {away_decimal_ml}')
            print(f'Away Win: {away_winner}')
            print(f'Neutral Site: {neutral_site}')
            print(f'Both Ranked: {ranked_matchup}')
            print(f'One Ranked: {one_ranked}')
            print('\n\n')
    
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