"""Models related to Units."""
from datetime import datetime
import logging

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.utils.timezone import now
import pytz

from core.actions import send_command_status, send_unit_status
from x10.interface import HOUSE_LABELS, send_command, UNIT_LABELS
from x10.lock import cache_lock
from .schedule import Schedule
from .solar_schedule import SolarSchedule

__all__ = ('InvalidSignalError', 'Unit', 'OnScheduleConstraint', 'OffScheduleConstraint',
           'OnSolarScheduleConstraint', 'OffSolarScheduleConstraint')

logger = logging.getLogger(__name__)


class InvalidSignalError(Exception):
    """Exception when a command cannot be sent to a unit."""

    pass


class Unit(models.Model):
    """Model to represent a receiver in an X10 home."""

    HOUSE_CHOICES = [(h.upper(), h.upper()) for h in HOUSE_LABELS]
    NUMBER_CHOICES = [(n, str(n)) for n in UNIT_LABELS]

    ON_ACTION = 'on'
    OFF_ACTION = 'off'
    BRIGHT_ACTION = 'brt'
    DIM_ACTION = 'dim'
    ACTION_CHOICES = (
        (ON_ACTION, 'On'),
        (OFF_ACTION, 'Off'),
        (BRIGHT_ACTION, 'Bright'),
        (DIM_ACTION, 'Dim'),
    )
    ACTION_COMMANDS = [a for a, _ in ACTION_CHOICES]

    class Meta:
        """Model options."""

        ordering = ('order',)

    name = models.CharField(
        max_length=128,
        help_text='Display name of the unit.')
    slug = models.SlugField(
        unique=True,
        help_text='Unique name of the unit.')
    number = models.PositiveSmallIntegerField(
        choices=NUMBER_CHOICES,
        help_text='X10 unit number.')
    house = models.CharField(
        max_length=1,
        choices=HOUSE_CHOICES,
        default='M',
        help_text='X10 house code.')
    dimmable = models.BooleanField(
        default=False,
        help_text='Whether or not the unit can be dimmed.')
    order = models.PositiveSmallIntegerField(
        default=0,
        editable=False,
        db_index=True)
    state = models.BooleanField(
        default=False,
        help_text='If the unit is on or off.')
    auto_managed = models.BooleanField(
        default=True,
        help_text='If this unit can be controlled by other tasks.')
    on_schedules = models.ManyToManyField(
        Schedule,
        through='OnScheduleConstraint',
        blank=True,
        related_name='on_unit_set',
        help_text='Automatic schedules to turn on the unit.')
    off_schedules = models.ManyToManyField(
        Schedule,
        through='OffScheduleConstraint',
        blank=True,
        related_name='off_unit_set',
        help_text='Automatic schedules to turn off the unit.')
    on_solar_schedules = models.ManyToManyField(
        SolarSchedule,
        through='OnSolarScheduleConstraint',
        blank=True,
        related_name='on_unit_set',
        help_text='Automatic solar schedules to turn on the unit.')
    off_solar_schedules = models.ManyToManyField(
        SolarSchedule,
        through='OffSolarScheduleConstraint',
        blank=True,
        related_name='off_unit_set',
        help_text='Automatic solar schedules to turn off the unit.')

    def __str__(self):
        """Use the display name when converting to string."""
        return self.name

    def send_signal(self, command: str=None, multiplier: int=1, attempts: int=10,
                    sleep_time: float=0.5):
        """Send a signal to the unit.

        This uses a lock to prevent multiple messages from being sent at once. A command can be
        specified, but will default to self.state.

        :param command: the command to send to the unit
        :param multiplier: the number of times to send the command
        :param attempts: max number of attempts to try grabbing the lock
        :param sleep_time: how long to wait before checking the lock again
        :raises: CacheLockException
        :raises: InvalidSignalError
        :returns: the status if the command was sent
        """
        logger.debug(f'sending signal "{command}" {multiplier} time(s) to unit "{self}"')
        status = True

        # no command given, resend the current state
        if command is None:
            command = Unit.ON_ACTION if self.state else Unit.OFF_ACTION
            logger.debug(f'using default action "{command}"')

        # check if the command was valid
        command = command.lower()
        if command not in Unit.ACTION_COMMANDS:
            logger.error(f'invalid command: "{command}"')
            raise InvalidSignalError(f'the command "{command}" does not exist')

        # only allow bright or dim actions if the unit is dimmable
        if (command == Unit.BRIGHT_ACTION or command == Unit.DIM_ACTION) and not self.dimmable:
            logger.error(f'"{self}" does not support the command: {command}')
            raise InvalidSignalError(f'the "{command}" command cannot be sent to this device')

        # grab the lock and send the signal
        with cache_lock('x10_interface', attempts, sleep_time):
            for i in range(0, multiplier):
                logger.debug((f'sending signal "{command}" on "{settings.X10_SERIAL}" '
                              f'to unit "{self.number}" in house "{self.house}"'))
                send_command(settings.X10_SERIAL, self.house, self.number, command)

        # send the command action out to the websocket
        send_command_status(self, command)

        # save the state matching the on or off action
        if command in (Unit.ON_ACTION, Unit.OFF_ACTION):
            self.state = command == Unit.ON_ACTION
            logger.debug(f'saving new state of "{self}": {self.state}')
            self.save()
        return status

    def daily_events(self, current_time: datetime = now(), only_if_home: bool = False):
        """Get times for all events in the current day.

        :param current_time: the current time to check against
        :returns: a list of dicts containing event time and state (on/off)
        """
        # get today's date only (remove time info)
        current_time = current_time.astimezone(pytz.utc)
        today = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        logger.debug(f'generating daily events for "{self}" at "{current_time}"')

        qs_filter = {}
        if only_if_home:
            qs_filter['if_home'] = True

        # get a list of all event times for today
        on_dts = [ev.schedule.next_time(today) for ev in
                  self.onscheduleconstraint_set.filter(**qs_filter)]
        on_dts += [ev.solarschedule.next_time(today) for ev in
                   self.onsolarscheduleconstraint_set.filter(**qs_filter)]
        off_dts = [ev.schedule.next_time(today) for ev in
                   self.offscheduleconstraint_set.filter(**qs_filter)]
        off_dts += [ev.solarschedule.next_time(today) for ev in
                    self.offsolarscheduleconstraint_set.filter(**qs_filter)]

        # create a single list of events for the entire day
        events = []
        for dt in on_dts:
            events.append({'time': dt, 'state': True})
        for dt in off_dts:
            events.append({'time': dt, 'state': False})

        # sort the events by their time
        events = sorted(events, key=lambda k: k['time'])
        logger.debug(f'scheduled events for "{self}" for today: {events}')
        return events

    def intended_state(self, current_time: datetime = now(), only_if_home: bool = False):
        """Return the state the unit should be set to for the current time.

        :param current_time: the current time to check against
        :returns: the desired state based on the schedules.
        """
        # get schedule of events for today
        # these are ordered by event time
        schedule = self.daily_events(current_time, only_if_home)

        state = False
        for ev in schedule:
            logger.debug(f'checking {ev}')

            # the event time occurs in the future
            # break out of the loop, leaving the last known state
            if ev['time'] >= current_time:
                logger.debug((f'"{ev}" is past "{current_time}", using state for '
                              f'unit "{self}": {state}'))
                break

            # set the state to represent the action
            state = ev['state']
        return state

    @staticmethod
    def post_save(sender, instance=None, created=False, **kwargs):
        """Send the serialized instance out to the websocket."""
        send_unit_status(instance, created)


post_save.connect(Unit.post_save, sender=Unit)


class ScheduleConstraint(models.Model):
    """Any constraints applied to relationships between a Unit and a Schedule."""

    schedule = models.ForeignKey(
        Schedule,
        help_text='The schedule object for this relationship')
    unit = models.ForeignKey(
        Unit,
        help_text='The unit object for this relationship')
    if_home = models.BooleanField(
        default=False,
        help_text='Only use this schedule if a real person is home')

    class Meta:
        """Model options."""

        abstract = True
        unique_together = (('schedule', 'unit'),)

    def __str__(self):
        """Use unit and schedule name."""
        base = f'{self.unit} at {self.schedule}'
        if self.if_home:
            base += ' (home)'
        return base


class OnScheduleConstraint(ScheduleConstraint):
    """Constraint between a Unit and on-Schedules."""

    pass


class OffScheduleConstraint(ScheduleConstraint):
    """Constraint between a Unit and off-Schedules."""

    pass


class SolarScheduleConstraint(models.Model):
    """Any constraints applied to relationships between a Unit and a SolarSchedule."""

    solarschedule = models.ForeignKey(
        SolarSchedule,
        help_text='The solar schedule object for this relationship')
    unit = models.ForeignKey(
        Unit,
        help_text='The unit object for this relationship')
    if_home = models.BooleanField(
        default=False,
        help_text='Only use this schedule if a real person is home')

    class Meta:
        """Model options."""

        abstract = True
        unique_together = (('solarschedule', 'unit'),)

    def __str__(self):
        """Use unit and schedule name."""
        base = f'{self.unit} at {self.solarschedule}'
        if self.if_home:
            base += ' (home)'
        return base


class OnSolarScheduleConstraint(SolarScheduleConstraint):
    """Constraint between a Unit and on-SolarSchedules."""

    pass


class OffSolarScheduleConstraint(SolarScheduleConstraint):
    """Constraint between a Unit and off-SolarSchedules."""

    pass
