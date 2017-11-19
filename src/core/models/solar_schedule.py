"""Models related to SolarSchedules."""
from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils.timezone import now
import ephem
import pytz

__all__ = ('SolarSchedule',)


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
