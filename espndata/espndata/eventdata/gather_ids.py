import logging
import requests
import time
import json
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import date, timedelta
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def request_with_retry(url):
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


def get_espn_scoreboard_url(league, year=None, week=None, date_str=None):
    """ 
    Returns the built ESPN scoreboard page URL for the specified sport during the specified time.
    Also returns a pre-built logging string to be used when the HTTP request is made.
    """
    if league == 'nfl' or league == 'college-football':
        specifiers = f'_/week/{week}/year/{year}/seasontype/2'

        if league == 'college-football':
            specifiers += '/group/80'
    elif league == 'nba' or league == 'mlb':
        specifiers = f'_/date/{date_str}'

    url = f'https://espn.com/{league}/scoreboard/{specifiers}'
    
    return url


def get_event_ids_from_scoreboard(scoreboard):
    """ 
    Parses the text (HTML) of the specified HTTP response and returns a list of ESPN event IDs found on the page.
    """
    soup = BeautifulSoup(scoreboard.text, 'html.parser')
    games = soup.find_all('section', {'class': 'Scoreboard'})
    return [game.get('id') for game in games]



def main():
    leagues = {
        'college-football': [], 
        'nfl': [], 
        'nba': [], 
        'mlb': [],
    }

    for league, id_list in leagues.items():
        if league == 'nfl' or league == 'college-football':
            # YEARS = [2017, 2018, 2019, 2022, 2023, 2024]
            YEARS = [2025]
            # WEEK_RANGE = range(20)      # ensures all weeks are included -- non-existant week scoreboards exist with no game data

            if league == 'college-football':
                WEEK_RANGE = range(4)
            elif league == 'nfl':
                WEEK_RANGE = range(3)

            with tqdm(total=len(YEARS) * len(WEEK_RANGE), desc=f'Processing {league} Scoreboards') as prog_bar:
                for year in YEARS:
                    for week in WEEK_RANGE:
                        scoreboard_url = get_espn_scoreboard_url(league, year=year, week=week + 1)
                        scoreboard = request_with_retry(scoreboard_url)
                        id_list.extend(get_event_ids_from_scoreboard(scoreboard))
                        time.sleep(1)
                        prog_bar.update(1)
        elif league == 'nba' or league == 'mlb':
            if league == 'nba':
                season_start_end_dates = [
                    # [date(2017, 10, 17), date(2018, 6, 10)],
                    # [date(2018, 10, 16), date(2019, 6, 15)],
                    # [date(2021, 10, 19), date(2022, 6, 20)],
                    # [date(2022, 10, 18), date(2023, 6, 15)],
                    # [date(2023, 10, 24), date(2024, 6, 20)],
                    # [date(2024, 10, 22), date(2025, 6, 25)],
                ]
            elif league == 'mlb':
                season_start_end_dates = [
                    # [date(2019, 3, 20), date(2019, 11, 1)],
                    # [date(2022, 4, 7), date(2022, 11, 10)],
                    # [date(2023, 3, 30), date(2023, 11, 5)],
                    # [date(2024, 3, 20), date(2024, 11, 1)],
                    [date(2025, 3, 18), date(2025, 9, 21)],
                ]

            season_lengths = [d[1] - d[0] for d in season_start_end_dates]
            season_lengths = [d.days for d in season_lengths]
            total_days = sum(season_lengths)

            with tqdm(total=total_days, desc=f'Processing {league} Scoreboards') as prog_bar:
                for season in season_start_end_dates:
                    iter_date = season[0]
                    end_date = season[1]

                    while iter_date != end_date:
                        date_str = iter_date.strftime('%Y%m%d')
                        scoreboard_url = get_espn_scoreboard_url(league, date_str=date_str)
                        scoreboard = request_with_retry(scoreboard_url)
                        id_list.extend(get_event_ids_from_scoreboard(scoreboard))
                        iter_date = iter_date + timedelta(days=1)
                        time.sleep(1)
                        prog_bar.update(1)

        id_list = list(dict.fromkeys(id_list))

    with open('event_ids.json', 'w') as ids_file:
        json.dump(leagues, ids_file)


if __name__ == '__main__':
    main()