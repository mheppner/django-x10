"""Core project channels routing."""
from channels.routing import route

from . import consumers


PATH = r'^/status/'

routes = [
    route('websocket.connect', consumers.ws_connect, path=PATH),
    route('websocket.receive', consumers.ws_receive, path=PATH),
    route('websocket.disconnect', consumers.ws_disconnect, path=PATH),
]
