"""Models related to Schedules."""
from datetime import datetime, timedelta

from crontab import CronTab
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now
import pytz

__all__ = ('Schedule',)


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
