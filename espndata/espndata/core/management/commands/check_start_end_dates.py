from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from datetime import date
import logging
from sentry_sdk import capture_exception

from espndata.core.models import DataCollectionState

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Checks DataCollectionState objects season_start and season_end dates need to be updated. Sends an email to admins if any do.'

    def handle(self, *args, **options):
        logger.info('`check_start_end_dates` command started.')

        today = date.today()

        message = ''
        improperly_configured = 'The stored {league} season dates are not properly configured. Update them via the DataCollectionState object.\n'

        for state in DataCollectionState.objects.all():
            if state.all_star_start and state.all_star_end:
                # order should always be seasonStart, allstarStart, allstarEnd, seasonEnd
                if not (
                    state.season_start < state.all_star_start
                    and state.all_star_start <= state.all_star_end
                    and state.all_star_end < state.season_end
                ):
                    message += improperly_configured.format(state.get_league_display())
            elif not state.all_star_start and not state.all_star_end:
                # order should always be seasonStart, seasonEnd
                if not state.season_start < state.season_end:
                    message += improperly_configured.format(state.get_league_display())
            else:
                # must have both or neither all star dates, not just one
                message += improperly_configured.format(state.get_league_display())

            if today > state.season_end:
                message += f'The current {state.get_league_display()} season has ended. Relevant season dates should be updated via the DataCollectionState object.\n'

        if message:
            try:
                send_mail(
                    subject='ESPN Data - Update League Dates',
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL],
                    fail_silently=False,
                )
            except Exception as e:
                capture_exception(e)
                logger.error(f'Email Failed: {e}')

        logger.info('`check_start_end_dates` command completed.')
