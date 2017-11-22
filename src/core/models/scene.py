"""Models related to Scenes."""
from django.db import models
from django.db.models.signals import post_save

from core.actions import send_scene_status
from .unit import Unit

__all__ = ('Scene',)


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

    @staticmethod
    def post_save(sender, instance=None, created=False, **kwargs):
        """Send the serialized instance out to the websocket."""
        send_scene_status(instance, created)

    def send_signal(self, command: str=None, multiplier: int=1, attempts: int=10,
                    sleep_time: float=0.5):
        """Send the signal to all of the units in the scene.

        :param command: the command to send to each unit
        :param multiplier: the number of times to send the command to each unit
        :param attempts: max number of attempts to try grabbing the lock
        :param sleep_time: how long to wait before checking the lock again
        :raises: CacheLockException
        :raises: InvalidSignalError
        :returns: the status if all the command were sent
        """
        status = True
        for unit in self.units.all():
            status = status and unit.send_signal(command, multiplier, attempts, sleep_time)
        return status


post_save.connect(Scene.post_save, sender=Scene)
