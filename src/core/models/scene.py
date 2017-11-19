"""Models related to Scenes."""
from django.db import models

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
