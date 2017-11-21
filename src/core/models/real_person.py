"""Models related to real people."""
from channels import Group
from django.core.cache import cache
from rest_framework.renderers import JSONRenderer

from core.consumers import STATUS_GROUP

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
        Group(STATUS_GROUP).send({
            'text': JSONRenderer().render({
                'namespace': 'person',
                'action': 'arrive',
                'payload': {'is_home': True}
            }).decode('utf-8')
        })
        return RealPerson._set_status(True)

    @staticmethod
    def leave():
        """Set the person being outside the home."""
        Group(STATUS_GROUP).send({
            'text': JSONRenderer().render({
                'namespace': 'person',
                'action': 'leave',
                'payload': {'is_home': False}
            }).decode('utf-8')
        })
        return RealPerson._set_status(False)

    @staticmethod
    def is_home():
        """Check if the person is within the home or not."""
        return cache.get(RealPerson.KEY, False)
