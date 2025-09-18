from django.conf import settings
from django.core.management.base import BaseCommand

import json


class Command(BaseCommand):
    help = 'Uses stored ESPN event IDs to collect and parse ESPN event summaries.'

    def handle(self, *args, **otpions):
        ids_file_path = settings.BASE_DIR / 'espndata' / 'eventdata' / 'data' / 'all_event_ids.json'
        
        with open(ids_file_path, 'r') as ids_file:
            ids_by_league = json.load(ids_file)