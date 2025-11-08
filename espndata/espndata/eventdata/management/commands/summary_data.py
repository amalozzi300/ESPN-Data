from django.conf import settings
from django.core.management.base import BaseCommand

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
    help = 'Uses stored ESPN event IDs to collect and parse ESPN event summaries.'

    def handle(self, *args, **options):
        league_sport_map = {league: details['sport'] for league, details in settings.LEAGUE_DETAILS.items()}
        incomplete_event_data = {league: {} for league in settings.LEAGUE_DETAILS.keys()}
        new_events = []
        new_team_predictions = []
        existing_league_id_pairs = set(Event.objects.values_list('league', 'espn_id'))
        raw_data_filepath = settings.BASE_DIR / 'espndata' / '_raw_data'
        
        with open(raw_data_filepath / 'event_ids.json', 'r') as ids_file:
            ids_by_league = json.load(ids_file)

        for league, ids_list in ids_by_league.items():
            sport = league_sport_map[league]
            formatted_url = settings.BASE_ESPN_EVENT_SUMMARY_API_LINK.format(sport=sport, league=league)
            
            for espn_id in tqdm(ids_list, desc=f'Fetching and Parsing ESPN {league.title()} Game Summaries'):
                pair = (league, espn_id)

                if pair not in existing_league_id_pairs:
                    params = {'event': espn_id}
                    event_summary = self.request_with_retry(formatted_url, params).json()

                    header_info = event_summary.get('header', {})
                    season_info = header_info.get('season')
                    if not season_info:
                        incomplete_event_data[league].update({espn_id: 'season/header'})
                        continue
                    
                    season_type = season_info.get('type')
                    if season_type == 1:
                        continue        # ignore pre-season events
                    
                    season_year = season_info.get('year')
                    week = header_info.get('week')

                    comp = next(iter(header_info.get('competitions', [])))
                    if not comp:
                        incomplete_event_data[league].update({espn_id: 'competition'})
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
                        incomplete_event_data[league].update({espn_id: 'home/away'})
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
                        incomplete_event_data[league].update({espn_id: 'win probs'})
                        continue
                    
                    home_win_prob = pre_win_probs.get('homeWinPercentage') * 100
                    away_win_prob = 100 - home_win_prob

                    betting_data = next(iter(event_summary.get('pickcenter', [])), {})
                    home_american_ml = betting_data.get('homeTeamOdds', {}).get('moneyLine')
                    home_decimal_ml = american_to_decimal(home_american_ml)
                    away_american_ml = betting_data.get('awayTeamOdds', {}).get('moneyLine')
                    away_decimal_ml = american_to_decimal(away_american_ml)

                    new_event = Event(
                        league=league,
                        espn_id=espn_id,
                        date=event_date,
                        season=season_year,
                        week=week,
                        season_type=season_type,
                        is_neutral_site=neutral_site,
                        both_ranked_matchup=both_ranked_matchup,
                        one_ranked_matchup=one_ranked_matchup,
                    )
                    home_team_prediction = TeamPrediction(
                        event=new_event,
                        team_name=home_team,
                        team_rank=home_rank,
                        home_away='home' if not neutral_site else 'neutral',
                        win_probability=home_win_prob,
                        moneyline=home_decimal_ml,
                        is_winner=is_home_win,
                        opponent_name=away_team,
                        opponent_rank=away_rank,
                    )
                    away_team_prediction = TeamPrediction(
                        event=new_event,
                        team_name=away_team,
                        team_rank=away_rank,
                        home_away='away' if not neutral_site else 'neutral',
                        win_probability=away_win_prob,
                        moneyline=away_decimal_ml,
                        is_winner=is_away_win,
                        opponent_name=home_team,
                        opponent_rank=home_rank,
                    )

                    if home_team_prediction.is_winner:
                        new_event.winning_team = home_team
                    elif away_team_prediction.is_winner:
                        new_event.winning_team = away_team

                    new_events.append(new_event)
                    new_team_predictions += [home_team_prediction, away_team_prediction]
                    existing_league_id_pairs.add(pair)

                time.sleep(0.5)

        Event.objects.bulk_create(new_events)
        TeamPrediction.objects.bulk_create(new_team_predictions)
        logging.info(f'{len(new_events)} Events and {len(new_team_predictions)} TeamPredictions successfully added to the database')

        with open(raw_data_filepath / 'incomplete_data_events.json', 'w') as incomplete_file:
            json.dump(incomplete_event_data, incomplete_file)

        with open(raw_data_filepath / 'event_ids.json', 'w') as ids_file:
            json.dump({league: [] for league in settings.LEAGUE_DETAILS.keys()}, ids_file)
    
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