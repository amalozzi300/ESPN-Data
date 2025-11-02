from django.conf import settings
from django.core.management import BaseCommand

from datetime import timedelta
from dateutil import parser as dateparser
import json
import logging
import requests
import time
from tqdm import tqdm

from espndata.eventdata.models import Event, TeamPrediction
from espndata.core.utils import american_to_decimal

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        for league, details in settings.LEAGUE_DETAILS.items():
            self.should_collect_today()


    def should_collect_today(self, league, details, league_status):
        yesterday = self.today - timedelta(days=1)

        if details['check_type'] == 'weekly':
            if league_status.season_type == 3 and league_status.week == max(details['season_type'][3]):
                return yesterday <= league_status.season_start
        else:
            pass

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