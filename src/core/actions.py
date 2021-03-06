"""Centralized actions for sending to websockets."""
import logging

from channels import Group
from rest_framework.renderers import JSONRenderer

logger = logging.getLogger(__name__)

STATUS_GROUP = 'status'


def send_command_status(unit, command, channel=None):
    """Send the unit signal to the websocket.

    :param unit: a Unit model instance
    :param command: the command that was activated
    :param channel: an outgoing reply channel, defaults to the entire group
    """
    if channel is None:
        channel = Group(STATUS_GROUP)

    logger.debug(f'sending command {command} on {unit} to {channel}')
    channel.send({
        'text': JSONRenderer().render({
            'namespace': 'units',
            'action': 'send_signal',
            'id': unit.slug,
            'action': 'send_signal',
            'payload': {'command': command}
        }).decode('utf-8')
    })


def send_unit_status(instance, created=False, channel=None):
    """Send the serialized unit to the websocket.

    :param instance: a Unit model instance
    :param created: if the unit was created
    :param channel: an outgoing reply channel, defaults to the entire group
    """
    if channel is None:
        channel = Group(STATUS_GROUP)

    from core.serializers import UnitSerializer  # noqa
    serializer = UnitSerializer(instance)

    logger.debug(f'sending unit {instance} to {channel}')
    channel.send({
        'text': JSONRenderer().render({
            'namespace': 'units',
            'action': 'post_save',
            'id': instance.slug,
            'created': created,
            'payload': serializer.data
        }).decode('utf-8')
    })


def send_units_status(qs=None, channel=None):
    """Send all serialized units to the websocket.

    :param qs: a queryset for Units, defaults to all instances
    :param channel: an outgoing reply channel, defaults to the entire group
    """
    if channel is None:
        channel = Group(STATUS_GROUP)

    from core.serializers import UnitSerializer  # noqa

    if qs is None:
        from core.models import Unit  # noqa
        qs = Unit.objects.all()

    serializer = UnitSerializer(qs, many=True)

    logger.debug(f'sending all {len(qs)} units to {channel}')
    channel.send({
        'text': JSONRenderer().render({
            'namespace': 'units',
            'action': 'set',
            'payload': serializer.data
        }).decode('utf-8')
    })


def send_scene_status(instance, created=False, channel=None):
    """Send the serialized scene to the websocket.

    :param instance: a Scene model instance
    :param created: if the scene was created
    :param channel: an outgoing reply channel, defaults to the entire group
    """
    if channel is None:
        channel = Group(STATUS_GROUP)

    from core.serializers import SceneSerializer  # noqa
    serializer = SceneSerializer(instance)

    logger.debug(f'sending scene {instance} state to {channel}')
    channel.send({
        'text': JSONRenderer().render({
            'namespace': 'scenes',
            'action': 'post_save',
            'id': instance.slug,
            'created': created,
            'payload': serializer.data
        }).decode('utf-8')
    })


def send_scenes_status(qs=None, channel=None):
    """Send all serialized scenes to the websocket.

    :param qs: a queryset for Scenes, defaults to all instances
    :param channel: an outgoing reply channel, defaults to the entire group
    """
    if channel is None:
        channel = Group(STATUS_GROUP)

    from core.serializers import SceneSerializer  # noqa
    if qs is None:
        from core.models import Scene  # noqa
        qs = Scene.objects.all()

    serializer = SceneSerializer(qs, many=True)

    logger.debug(f'sending all {len(qs)} scenes to {channel}')
    channel.send({
        'text': JSONRenderer().render({
            'namespace': 'scenes',
            'action': 'set',
            'payload': serializer.data
        }).decode('utf-8')
    })


def send_real_person_status(status=None, channel=None):
    """Send the status of the person to the websocket.

    :param status: the current status of the RealPerson, will fetch the status automatically
    :param channel: an outgoing reply channel, defaults to the entire group
    """
    if channel is None:
        channel = Group(STATUS_GROUP)

    if status is None:
        from core.models import RealPerson  # noqa
        status = RealPerson.is_home()

    logger.debug(f'sending state of real person to {channel}: {status}')
    channel.send({
        'text': JSONRenderer().render({
            'namespace': 'person',
            'action': 'arrive' if status else 'leave',
            'payload': {'is_home': status}
        }).decode('utf-8')
    })
