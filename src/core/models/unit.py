"""Models related to Units."""
from datetime import datetime

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.utils.timezone import now
import pytz

from core.actions import send_unit_status, send_command_status
from x10.interface import HOUSE_LABELS, send_command, UNIT_LABELS
from x10.lock import cache_lock
from .schedule import Schedule
from .solar_schedule import SolarSchedule

__all__ = ('InvalidSignalError', 'Unit',)


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
        blank=True,
        related_name='on_unit_set',
        help_text='Automatic schedules to turn on the unit.')
    off_schedules = models.ManyToManyField(
        Schedule,
        blank=True,
        related_name='off_unit_set',
        help_text='Automatic schedules to turn off the unit.')
    on_solar_schedules = models.ManyToManyField(
        SolarSchedule,
        blank=True,
        related_name='on_unit_set',
        help_text='Automatic solar schedules to turn on the unit.')
    off_solar_schedules = models.ManyToManyField(
        SolarSchedule,
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
        status = True

        # no command given, resend the current state
        if command is None:
            command = Unit.ON_ACTION if self.state else Unit.OFF_ACTION

        # check if the command was valid
        command = command.lower()
        if command not in Unit.ACTION_COMMANDS:
            raise InvalidSignalError(f'the command {command} does not exist')

        # only allow bright or dim actions if the unit is dimmable
        if (command == Unit.BRIGHT_ACTION or command == Unit.DIM_ACTION) and not self.dimmable:
            raise InvalidSignalError(f'the {command} command cannot be sent to this device')

        # grab the lock and send the signal
        with cache_lock('x10_interface', attempts, sleep_time):
            for i in range(0, multiplier):
                send_command(settings.X10_SERIAL, self.house, self.number, command)

        # send the command action out to the websocket
        send_command_status(self, command)

        # save the state matching the on or off action
        if command in (Unit.ON_ACTION, Unit.OFF_ACTION):
            self.state = command == Unit.ON_ACTION
            self.save()
        return status

    def daily_events(self, current_time: datetime = now()):
        """Get times for all events in the current day.

        :param current_time: the current time to check against
        :returns: a list of dicts containing event time and state (on/off)
        """
        # get today's date only (remove time info)
        current_time = current_time.astimezone(pytz.utc)
        today = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

        # get a list of all event times for today
        on_dts = [ev.next_time(today) for ev in self.on_schedules.all()]
        on_dts += [ev.next_time(today) for ev in self.on_solar_schedules.all()]
        off_dts = [ev.next_time(today) for ev in self.off_schedules.all()]
        off_dts += [ev.next_time(today) for ev in self.off_solar_schedules.all()]

        # create a single list of events for the entire day
        events = []
        for dt in on_dts:
            events.append({'time': dt, 'state': True})
        for dt in off_dts:
            events.append({'time': dt, 'state': False})

        # sort the events by their time
        return sorted(events, key=lambda k: k['time'])

    def intended_state(self, current_time: datetime = now()):
        """Returns the state the unit should be set to for the current time.

        :param current_time: the current time to check against
        :returns: the desired state based on the schedules.
        """
        # get schedule of events for today
        # these are ordered by event time
        schedule = self.daily_events(current_time)

        state = False
        for ev in schedule:
            # the event time occurs in the future
            # break out of the loop, leaving the last known state
            if ev['time'] >= current_time:
                break

            # set the state to represent the action
            state = ev['state']
        return state

    @staticmethod
    def post_save(sender, instance=None, created=False, **kwargs):
        """Send the serialized instance out to the websocket."""
        send_unit_status(instance, created)


post_save.connect(Unit.post_save, sender=Unit)
