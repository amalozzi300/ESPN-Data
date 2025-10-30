from django.core.management.base import BaseCommand

from datetime import date

from espndata.core.models import DataCollectionState

class Command(BaseCommand):
    help = 'Checks DataCollectionState objects season_start and season_end dates need to be updated. Sends an email to admins if any do.'

    def handle(self, *args, **options):
        today = date.today()
        message = ''

        for state in DataCollectionState.objects.all():
            if state.season_end <= state.season_start:
                message += f'The stored {state.get_league_display()} season season dates are out of sync. Update them via the DataCollectionState object.'
            if today > state.season_end:
                message += f'The current {state.get_league_display()} season has ended. Relevant season dates stored in the DataCollectionState object should be updated.\n'
            if state.all_star_start:
                if (
                    state.all_star_start > state.all_star_end
                    or state.season_start > state.all_star_start
                ):
                    message += f'The stored {state.get_league_display()} all star break dates are out of sync. Update them via the DataCollectionState object.'