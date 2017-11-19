"""Core app models."""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from .real_person import *  # noqa
from .scene import *  # noqa
from .schedule import *  # noqa
from .solar_schedule import *  # noqa
from .unit import *  # noqa


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """Automatically create auth tokens for users."""
    if created:
        Token.objects.create(user=instance)
