from django.conf import settings
from django.core.management.base import BaseCommand

import json
import logging
import requests
import time

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
        base_espn_api_url = 'https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary'
        ids_file_path = settings.BASE_DIR / 'espndata' / '_raw_data' / 'all_event_ids.json'
        
        with open(ids_file_path, 'r') as ids_file:
            ids_by_league = json.load(ids_file)

        for league, ids_list in ids_by_league.items():
            sport = league_sport_map[league]
            formatted_url = base_espn_api_url.format(sport=sport, league=league)
            logging.info(formatted_url)

            


    
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
                resp = requests.get(url, headers=headers, timeout=30)
                resp.raise_for_status()
                return resp
            except Exception as e:
                logging.warning(f'Request failed {url}. Attempt {attempt + 1}/{max_retries}. Error: {e}')
                time.sleep(backoff * (5 ** attempt))
        
        raise RuntimeError(f'Failed to fetch {url} after {max_retries} attempts')