from django.conf import settings
from django.core.management import BaseCommand

from datetime import date, timedelta
from dateutil import parser as dateparser
import json
import logging
import requests
import time
from sentry_sdk import capture_exception

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
            if league_state.league not in settings.LEAGUE_DETAILS:
                # League is not configured in LEAGUE_DETAILS setting
                error_msg = f'League "{league_state.league}" has DataCollectionState but no LEAGUE_DETAILS configuration.'
                logger.error(error_msg) # Log locally
                capture_exception(RuntimeError(error_msg))  # Send to Sentry
                continue    # Skip to next league

            check_collect = self.check_collect_today(league_state)

            if check_collect:
                pass

    def check_collect_today(self, league_state):
        """
        Returns params dictionary to be sent with formatted URL to `request_with_retry()` method.
        If should collect today, returns populated dictionary (truthy), else returns empty dictionary (falsy).
        """
        details = settings.LEAGUE_DETAILS[league_state.league]

        if details['check_type'] == 'daily':
            if self.check_is_offseason(league_state):
                # Offseason
                return {}

            return self.check_collect_daily_league(league_state)
        else:
            if details['check_day'] != self.today.weekday():
                # Only check on specified day of week
                return {}
            
            season_types = details['season_types']
            
            if league_state.league == 'nfl':
                return self.check_collect_nfl(league_state, season_types)
            elif league_state.league == 'college-football':
                return self.check_collect_ncaaf(league_state, season_types)
            else:
                error_msg = f'No collection handler implemented for weekly league: {league_state.league}'
                logger.error(error_msg)
                capture_exception(RuntimeError(error_msg))
                return {}
        
    def check_collect_daily_league(self, league_state):
        """
        Handles checking if daily league's data should be collected.
        If should collect today, returns populated dictionary (truthy), else returns empty dictionary (falsy).
        """
        if not (self.yesterday >= league_state.season_start and self.yesterday <= league_state.season_end):
            # Is currently offseason
            return {}
        
        if league_state.all_star_start and league_state.all_star_end:
            if (self.yesterday >= league_state.all_star_start and self.yesterday <= league_state.all_star_end):
                # Is currently All Star break
                return {}
            
        return {'date': self.yesterday.strftime('%Y%m%d')}

    def check_collect_nfl(self, league_state, season_types):
        """
        Handles checking if NFL data should be collected.
        If should collect today, returns populated dictionary (truthy), else returns empty dictionary (falsy).
        """
        if league_state.season_type == 2:
            if league_state.week != season_types[2][-1]:
                # Last collected week WAS NOT last week of regular season, gather next regular season week
                return {'season_type': 2, 'week': league_state.week + 1}
            
            return {'season_type': 3, 'week': season_types[3][0]}   # Last collected week WAS last week of regular season, gather first week of postseason
        else:
            if league_state.week != season_types[3][-1]:
                # Last collected week WAS NOT last week of postseason
                curr_week = league_state.week + 1

                if curr_week in season_types[3]:
                    # Week IS NOT Pro Bowl week, gather postseason week
                    return {'season_type': 3, 'week': curr_week}
                else:
                    # Week IS Pro Bowl week, do not gather, update League State to pretend we did (needed for accurate `curr_week` assignment)
                    league_state.week = curr_week
                    league_state.collected = self.today
                    league_state.save()
                    return {}
            else:
                # Last collected week WAS last week of postseason
                if self.check_is_offseason(league_state):
                    # Offseason -- new season not started. Do not gather data
                    return {}

                return {'season_type': 2, 'week': season_types[2][0]}   # New season started. Gather first regular season week's data

    def check_collect_ncaaf(self, league_state, season_types):
        """
        Handles checking if college football's data should be collected.
        If should collect today, returns populated dictionary (truthy), else returns empty dictionary (falsy).
        """
        if league_state.season_type == 2:
            if league_state.week != season_types[2][-1]:
                # Last collected week WAS NOT last week of regular season, gather next regular season week
                return {'season_type': 2, 'week': league_state.week + 1}
            
            # Last collected week WAS last week of regular season
            if self.yesterday >= league_state.season_end:
                # Can currently only collect postseason data after season end due to ESPN handling of CFP data on their scoreboard
                return {'season_type': 3, 'week': season_types[3][-1]}
            
            return {}   # Postseason started but season not ended, cannot collect postseason data
        else:
            # Last collected WAS last week of postseason
            if self.check_is_offseason(league_state):
                # Offseason -- new season not started. Do not gather data
                return {}

            return {'season_type': 2, 'week': season_types[2][0]}   # New season started. Gather first regular season week's data

    def check_is_offseason(self, league_state):
        """
        Checks if passed league is currently in offseason.
        Has checks for updated league dates and stale league dates (staleness is assumed to be short-term).
        Returns True if offseason, else returns False.
        """
        if self.yesterday > league_state.season_end:
            # Stale date check -- yesterday is after season end date, safe to assume offseason
            return True

        if league_state.is_offseason and self.yesterday < league_state.season_start:
            # Updated dates -- offseason previously recorded as active, new season not started -- remains offseason
            return True

        return False    # Season is active



    # OLD VERSION -- Here for manual comparison in case I missed anything in the refactor
    # def check_collect_today(self, league_state):
    #     """
    #     Returns the params dictionary to be sent with the formatted URL to the `request_with_retry()` method.
    #     If should collect today, returns a populated dictionary (truthy), else returns an empty dictionary (falsy).
    #     """
    #     if league_state.is_offseason and league_state.season_start > self.yesterday:
    #         # currently offseason and new season not started
    #         return {}
        
    #     details = settings.LEAGUE_DETAILS[league_state.league]

    #     if details['check_type'] == 'daily':
    #         if self.yesterday >= league_state.season_start and self.yesterday <= league_state.season_end:
    #             if not (self.yesterday >= league_state.all_star_start and self.yesterday <= league_state.all_star_end):
    #                 # season active and not in all star break
    #                 return {'date': self.yesterday.strftime('%Y%m%d')}
            
    #         return {}   # offseason or all star break
    #     else:
    #         if details['check_day'] != self.today.weekday():
    #             # weekly checks should only check on league's designated check day
    #             return {}

    #         if league_state.league == 'college-football':
    #             if league_state.season_type == 2:
    #                 if league_state.week != details['season_types'][2][-1]:
    #                     # most recently collected week is not last week of regular season
    #                     return {'season_type': 2, 'week': league_state.week + 1}
    #                 else:
    #                     if self.yesterday >= league_state.season_end:
    #                         # postseason data cannot be collected until the season ends due to ESPN's structure
    #                         return {'season_type': 3, 'week': details['season_types'][3][-1]}
    #                     else:
    #                         return {}
    #             else:
    #                 if self.yesterday >= league_state.season_start:
    #                     # new season started
    #                     return {'season_type': 2, 'week': details['season_types'][2][0]}
    #                 else:
    #                     return {}
    #         elif league_state.league == 'nfl':
    #             if league_state.season_type == 2:
    #                 if league_state.week != details['season_types'][2][-1]:
    #                     # most recently collected week is not last week of regular season
    #                     return {'season_type': 2, 'week': league_state.week + 1}
    #                 else:
    #                     return {'season_type': 3, 'week': details['season_types'][3][0]}
    #             else:
    #                 if league_state.week != details['season_types'][3][-1]:
    #                     # most recently collected week is not last week of post season
    #                     if league_state.week + 1 in details['season_types'][3]:
    #                         # current week is not Pro Bowl
    #                         return {'season_type': 3, 'week': league_state.week + 1}
    #                     else:
    #                         # skip collection for Pro Bowl, but update DataCollectionState object
    #                         league_state.week += 1
    #                         league_state.collected = self.today
    #                         league_state.save()

    #                         return {}
    #                 else:
    #                     if self.yesterday >= league_state.season_start:
    #                         # new season started
    #                         return {'season_type': 2, 'week': details['season_types'][2][0]}
    #                     else:
    #                         return {}




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