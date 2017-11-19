"""Core project channels routing."""
from channels.routing import route

from . import consumers


UNITS_PATH = r'^/units/status/'

routes = [
    route('websocket.connect', consumers.ws_connect, path=UNITS_PATH),
    route('websocket.receive', consumers.ws_receive, path=UNITS_PATH),
    route('websocket.disconnect', consumers.ws_disconnect, path=UNITS_PATH),
]
