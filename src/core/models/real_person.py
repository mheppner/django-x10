"""Models related to real people."""
from django.core.cache import cache

from core.actions import send_real_person_status

__all__ = ('RealPerson',)


class RealPerson(object):
    """Represent a physical person being in the home."""

    KEY = 'person_in_home'

    @staticmethod
    def _set_status(status: bool):
        """Set the status of the person."""
        cache.set(RealPerson.KEY, status, None)
        return status

    @staticmethod
    def arrive():
        """Set the person being inside the home."""
        send_real_person_status(status=True)
        return RealPerson._set_status(True)

    @staticmethod
    def leave():
        """Set the person being outside the home."""
        send_real_person_status(status=False)
        return RealPerson._set_status(False)

    @staticmethod
    def is_home():
        """Check if the person is within the home or not."""
        return cache.get(RealPerson.KEY, False)
