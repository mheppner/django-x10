"""Command to run solar schedules."""
import datetime
import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import now
import pytz

from core.models import OffSolarScheduleConstraint, OnSolarScheduleConstraint, RealPerson, Unit
from x10.interface import FirecrackerException
from x10.lock import CacheLockException


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command to run solar schedules."""

    help = 'Runs the solar schedule events for units.'

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
        self.delta = datetime.timedelta(seconds=interval)

        # used only for logging times
        self.tz = pytz.timezone(settings.TIME_ZONE)

        while True:
            current_time = now()
            logger.debug(f'starting check at {current_time.astimezone(self.tz)}')

            # if a person is not home, exclude the schedules that require someone to be home
            qs_filter = {}
            if not RealPerson.is_home():
                qs_filter['if_home'] = True

            # get all of the on schedules
            on_constraints = OnSolarScheduleConstraint.objects.exclude(**qs_filter)
            off_constraints = OffSolarScheduleConstraint.objects.exclude(**qs_filter)

            self.run_actions(on_constraints, current_time, Unit.ON_ACTION)
            self.run_actions(off_constraints, current_time, Unit.OFF_ACTION)

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
            logger.debug(f'sleeping {wait_sec} seconds...')
            time.sleep(wait_sec)

    def run_actions(self, constraints, current_time: datetime, action: str):
        """Run actions for a set of schedule constraints.

        :param constraints: the queryset of schedule constraints to loop through
        :param current_time: the current time to calculate the next event time
        :param action: the command to be sent
        """
        for c in constraints:
            # get the next event time for the schedule
            event_time = c.solarschedule.next_time(current_time)
            logger.debug((f'{c.solarschedule} next event time is at '
                          f'{event_time.astimezone(self.tz)}'))

            # get the next time the loop will run
            next_run = current_time + self.delta
            logger.debug(f'next run is at {next_run.astimezone(self.tz)}')

            if next_run > event_time:
                # the next time the loop will run exceeds the next scheduled time, run now
                logger.info(f'turning {c.unit} {action}')
                try:
                    c.unit.send_signal(action)
                except (CacheLockException, FirecrackerException) as e:
                    logger.exception(e)
