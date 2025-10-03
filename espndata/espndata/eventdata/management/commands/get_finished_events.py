from django.conf import settings
from django.core.management.base import BaseCommand

from bs4 import BeautifulSoup
from datetime import date, timedelta
from dateutil import parser as dateparser
import json
import logging
import requests
import time
from tqdm import tqdm

from espndata.eventdata.models import Event, TeamPrediction
from espndata.utils import american_to_decimal

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

class Command(BaseCommand):
    help = 'TBD'

    LEAGUE_DETAILS = settings.LEAGUE_DETAILS
    INCOMPLETE_EVENT_DATA = {
        'college-football': {},
        'nfl': {},
        'nba': {},
        'mlb': {},
    }

    def handle(self, *args, **options):
        today = date.today()

        for league, details in self.LEAGUE_DETAILS:
            pass

    def request_with_retry(self, url, params=None):
        """
        Sends requests to the ESPN scoreboard or event summary API URL and returns the response.
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
                logging.warning(f'Request failed {url}. Attempt {attempt + 1}/{max_retries}. Error {e}')
                time.sleep(backoff * (5 ** attempt))

        raise RuntimeError(f'Failed to fetch {url} after {max_retries} attempts')

    def get_espn_ids(self):
        pass

    def get_event_details(self):
        pass