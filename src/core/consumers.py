"""Channel consumers."""
import json

from channels import Group
from channels.auth import channel_session_user, channel_session_user_from_http
from rest_framework.renderers import JSONRenderer


STATUS_GROUP = 'status'


@channel_session_user_from_http
def ws_connect(message):
    """Add only authenticated users to the channel group."""
    if message.user.is_authenticated():
        message.reply_channel.send({'accept': True})
        Group(STATUS_GROUP).add(message.reply_channel)
    else:
        message.reply_channel.send({'accept': False})


@channel_session_user
def ws_receive(message):
    """Receive messages from the websocket."""
    try:
        data = json.loads(message.content['text'])
    except json.JSONDecodeError:
        message.reply_channel.send({
            'text': JSONRenderer().render({
                'error': 'unable to parse JSON message'
            }).decode('utf-8')
        })
    else:
        if 'action' in data:
            if data['action'] == 'status':
                from .models import Unit  # noqa
                from .serializers import UnitSerializer  # noqa
                units = Unit.objects.all()
                serializer = UnitSerializer(units, many=True)

                message.reply_channel.send({
                    'text': JSONRenderer().render(serializer.data).decode('utf-8')
                })
            else:
                message.reply_channel.send({
                    'text': JSONRenderer().render({
                        'error': 'unknown action'
                    }).decode('utf-8')
                })


@channel_session_user
def ws_disconnect(message):
    """Remove sockets from the group."""
    Group(STATUS_GROUP).discard(message.reply_channel)
