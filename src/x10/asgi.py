"""ASGI module for running with Channels."""
import os

from channels.asgi import get_channel_layer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'x10.settings')

channel_layer = get_channel_layer()
