"""Command to run cron-based schedules."""
import datetime
import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import now
import pytz

from core.models import Schedule
from x10.interface import FirecrackerException


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command to run solar schedules."""

    help = 'Runs the crontab schedule events for units.'

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            '-i', '--interval',
            help='How often the schedules should be checked, in seconds',
            type=int,
            default=5 * 60)

    def handle(self, *args, **options):
        """Runtime for command."""
        # set up logging levels
        verbosity = options.get('verbosity')
        if verbosity == 0:
            logger.setLevel(logging.WARN)
        elif verbosity == 1:
            logger.setLevel(logging.INFO)
        elif verbosity > 1:
            logger.setLevel(logging.DEBUG)

        # get the interval and create a time delta
        interval = options.get('interval')
        delta = datetime.timedelta(seconds=interval)

        # used only for logging times
        tz = pytz.timezone(settings.TIME_ZONE)

        while True:
            current_time = now()
            logger.info(f'starting check at {current_time.astimezone(tz)}')

            # get only schedules that have either on or off units set
            schedules = Schedule.objects.exclude(off_unit_set=None, on_unit_set=None)

            for schedule in schedules:
                event_time = schedule.next_time(current_time)
                logger.debug(f'{schedule} next event time is at {event_time.astimezone(tz)}')

                # get the next time the loop will run
                next_run = current_time + delta
                logger.debug(f'next run is at {next_run.astimezone(tz)}')

                if next_run > event_time:
                    logger.info(f'running ON tasks')
                    for unit in schedule.on_unit_set.all():
                        logger.debug(f'turning {unit} on')
                        try:
                            unit.send_signal('on')
                        except FirecrackerException as e:
                            logger.exception(e)

                    logger.info(f'running OFF tasks')
                    for unit in schedule.off_unit_set.all():
                        logger.debug(f'turning {unit} off')
                        try:
                            unit.send_signal('off')
                        except FirecrackerException as e:
                            logger.exception(e)

            # get the duration of the loop
            finish_time = now()
            duration = finish_time - current_time
            logger.debug(f'loop duration was {duration}')

            # schedule the next loop to run to stay within the interval time
            wait_sec = interval - duration.total_seconds()
            if duration.total_seconds() > interval:
                logger.warning(f'execution time exceeds interval, skipping next loop')
                wait_sec += interval

            # sleep until the next loop
            logger.info(f'sleeping {wait_sec} seconds...')
            time.sleep(wait_sec)
