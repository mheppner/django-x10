"""Models related to auth tokens."""
import binascii
import os

from django.conf import settings
from django.db import models


__all__ = ('PersistentToken',)


class PersistentToken(models.Model):
    """Alternative auth tokens to bypass drf-auth."""

    key = models.CharField(
        max_length=40,
        primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name='persistent_auth_token',
        on_delete=models.CASCADE)
    created = models.DateTimeField(
        auto_now_add=True)

    def save(self, *args, **kwargs):
        """Generate a key when saving for the first time."""
        if not self.key:
            self.key = self.generate_key()
        return super(PersistentToken, self).save(*args, **kwargs)

    def generate_key(self):
        """Create a random key."""
        return binascii.hexlify(os.urandom(20)).decode()

    def __str__(self):
        """Use key as a string representation."""
        return self.key
