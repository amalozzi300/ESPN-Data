from django.conf import settings
from django.core.management import BaseCommand

from datetime import date, timedelta
from dateutil import parser as dateparser
import json
import logging
import requests
import time
from tqdm import tqdm

from espndata.eventdata.models import Event, TeamPrediction
from espndata.core.models import DataCollectionState
from espndata.core.utils import american_to_decimal

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)

        for league_state in DataCollectionState.objects.all():
            should_collect = self.should_collect_today(league_state)

            if should_collect:
                pass


    def should_collect_today(self, league_state):
        """
        Returns the params dictionary to be sent with the formatted URL to the `request_with_retry()` method.
        If should collect today, returns a populated dictionary (truthy), else returns an empty dictionary (falsy).
        """
        if league_state.is_offseason and league_state.season_start > self.yesterday:
            # currently offseason and new season not started
            return {}
        
        details = settings.LEAGUE_DETAILS[league_state.league]

        if details['check_type'] == 'daily':
            if self.yesterday >= league_state.season_start and self.yesterday <= league_state.season_end:
                if not (self.yesterday >= league_state.all_star_start and self.yesterday <= league_state.all_star_end):
                    # season active and not in all star break
                    return {'date': self.yesterday.strftime('%Y%m%d')}
            
            return {}   # offseason or all star break
        else:
            if details['check_day'] != self.today.weekday():
                # weekly checks should only check on league's designated check day
                return {}

            if league_state.league == 'college-football':
                if league_state.season_type == 2:
                    if league_state.week != details['season_types'][2][-1]:
                        # most recently collected week is not last week of regular season
                        return {'season_type': 2, 'week': league_state.week + 1}
                    else:
                        if self.yesterday >= league_state.season_end:
                            # postseason data cannot be collected until the season ends due to ESPN's structure
                            return {'season_type': 3, 'week': details['season_types'][3][-1]}
                        else:
                            return {}
                else:
                    if self.yesterday >= league_state.start_date:
                        # new season started
                        return {'season_type': 2, 'week': details['season_types'][2][0]}
                    else:
                        return {}
            elif league_state.league == 'nfl':
                if league_state.season_type == 2:
                    if league_state.week != details['season_types'][2][-1]:
                        # most recently collected week is not last week of regular season
                        return {'season_type': 2, 'week': league_state.week + 1}
                    else:
                        return {'season_type': 3, 'week': details['season_types'][3][0]}
                else:
                    if league_state.week != details['season_types'][3][-1]:
                        # most recently collected week is not last week of post season
                        if league_state.week + 1 in details['season_types'][3]:
                            # current week is not Pro Bowl
                            return {'season_type': 3, 'week': league_state.week + 1}
                        else:
                            # skip collection for Pro Bowl, but update DataCollectionState object
                            league_state.week += 1
                            league_state.collected = self.today
                            league_state.save()

                            return {}
                    else:
                        if self.yesterday >= league_state.start_date:
                            # new season started
                            return {'season_type': 2, 'week': details['season_types'][2][0]}
                        else:
                            return {}




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