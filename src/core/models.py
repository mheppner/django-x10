"""Core models."""
from datetime import datetime, timedelta

from channels import Group
from crontab import CronTab
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
import ephem
import pytz
from rest_framework.authtoken.models import Token
from rest_framework.renderers import JSONRenderer

from x10.interface import HOUSE_LABELS, send_command, UNIT_LABELS
from x10.lock import cache_lock
from .consumers import UNITS_GROUP


class InvalidSignalError(Exception):
    """Exception when a command cannot be sent to a unit."""

    pass


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """Automatically create auth tokens for users."""
    if created:
        Token.objects.create(user=instance)


class SolarSchedule(models.Model):
    """Model to represent and calculate times for solar events."""

    EVENTS = {
        'dawn_astronomical': {
            'method': 'next_rising',
            'horizon': '-18',
            'use_center': True},
        'dawn_nautical': {
            'method': 'next_rising',
            'horizon': '-12',
            'use_center': True},
        'dawn_civil': {
            'method': 'next_rising',
            'horizon': '-6',
            'use_center': True},
        'sunrise': {
            'method': 'next_rising',
            'horizon': '-0:34',
            'use_center': False},
        'solar_noon': {
            'method': 'next_transit',
            'horizon': '0',
            'use_center': False},
        'sunset': {
            'method': 'next_setting',
            'horizon': '-0:34',
            'use_center': False},
        'dusk_civil': {
            'method': 'next_setting',
            'horizon': '-6',
            'use_center': True},
        'dusk_nautical': {
            'method': 'next_setting',
            'horizon': '-12',
            'use_center': True},
        'dusk_astronomical': {
            'method': 'next_setting',
            'horizon': '18',
            'use_center': True},
    }
    EVENT_CHOICES = [(key, ' '.join(key.split('_')).title()) for key in EVENTS.keys()]

    class Meta:
        """Model options."""

        ordering = ('event',)

    event = models.CharField(
        max_length=18,
        unique=True,
        choices=EVENT_CHOICES,
        help_text='Solar event type')

    def __str__(self):
        """Use event text when converting to string."""
        return self.get_event_display()

    def calendar(self):
        """Create a calendar for the event.

        :returns: observer calendar
        """
        cal = ephem.Observer()
        cal.lat = str(settings.X10_LATITUDE)
        cal.lon = str(settings.X10_LONGITUDE)
        cal.elev = 0
        cal.horizon = SolarSchedule.EVENTS[self.event]['horizon']
        cal.pressure = 0
        return cal

    def next_time(self, current_time: datetime = now()):
        """Get the next time of the event based on the current time.

        :param current_time: timezone-aware starting time
        :returns: next event time, in UTC
        """
        # get the event details and calendar
        event = SolarSchedule.EVENTS[self.event]
        cal = self.calendar()

        # ensure the input time is in utc
        current_time = current_time.astimezone(pytz.utc)

        # call the function
        func = getattr(cal, event['method'])
        if event['use_center']:
            next_time = func(ephem.Sun(), start=current_time, use_center=True)
        else:
            next_time = func(ephem.Sun(), start=current_time)

        # convert to utc datetime
        next_utc = next_time.datetime().replace(tzinfo=pytz.utc)
        return next_utc


class Schedule(models.Model):
    """Model to represent and calculate times for crontab-based events."""

    crontab = models.CharField(
        max_length=64,
        help_text='Crontab entry',
        unique=True)

    def __str__(self):
        """Use event text when converting to string."""
        return self.crontab

    def save(self, *args, **kwargs):
        """Save hook to also perform clean action."""
        self.full_clean()
        super(Schedule, self).save(*args, **kwargs)

    def clean(self, *args, **kwargs):
        """Clean hook to validate the crontab entry."""
        try:
            CronTab(self.crontab)
        except ValueError as e:
            raise ValidationError(str(e))
        super(Schedule, self).clean(*args, **kwargs)

    def calendar(self):
        """Create a CronTab for the event.

        :returns: crontab object
        """
        return CronTab(self.crontab)

    def next_time(self, current_time: datetime = now()):
        """Get the next time of the event based on the current time.

        :param current_time: timezone-aware starting time
        :returns: next event time, in UTC
        """
        # ensure the input time is in utc
        current_time = current_time.astimezone(pytz.utc)

        # get the crontab object
        cal = self.calendar()

        # calculate the next delta time to the next event
        delta = timedelta(seconds=cal.next(current_time))
        return current_time + delta


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
        permissions = (
            ('view_unit', 'Can view unit'),
        )

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
                status = status and send_command(settings.X10_SERIAL, self.house, self.number,
                                                 command)

        if status:
            # send the command action out to the websocket
            Group(UNITS_GROUP).send({
                'text': JSONRenderer().render({
                    'trigger': type(self).__name__,
                    'id': self.slug,
                    'action': 'send_signal',
                    'payload': {'command': command}
                }).decode('utf-8')
            })

            # save the state matching the on or off action
            if command in (Unit.ON_ACTION, Unit.OFF_ACTION):
                self.state = command == Unit.ON_ACTION
                self.save()
        return status

    @staticmethod
    def post_save(sender, instance=None, created=False, **kwargs):
        """Send the serialized instance out to the websocket."""
        from .serializers import UnitSerializer  # noqa
        serializer = UnitSerializer(instance)

        Group(UNITS_GROUP).send({
            'text': JSONRenderer().render({
                'trigger': type(instance).__name__,
                'id': instance.slug,
                'action': 'save',
                'created': created,
                'payload': serializer.data
            }).decode('utf-8')
        })


post_save.connect(Unit.post_save, sender=Unit)


class Scene(models.Model):
    """Represent groups of multiple units."""

    class Meta:
        """Model options."""

        ordering = ('name',)

    name = models.CharField(
        max_length=128,
        help_text='Display name of the scene.')
    slug = models.SlugField(
        unique=True,
        help_text='Unique name of the scene.')
    units = models.ManyToManyField(Unit)

    def __str__(self):
        """Use the display name when converting to string."""
        return self.name


class RealPerson(object):
    """Represent a physical person being in the home."""

    KEY = 'body_in_home'

    @staticmethod
    def _set_status(status: bool):
        """Set the status of the person."""
        cache.set(RealPerson.KEY, status, None)
        return status

    @staticmethod
    def arrive():
        """Set the person being inside the home."""
        return RealPerson._set_status(True)

    @staticmethod
    def leave():
        """Set the person being outside the home."""
        return RealPerson._set_status(False)

    @staticmethod
    def is_home():
        """Check if the person is within the home or not."""
        return cache.get(RealPerson.KEY, False)
