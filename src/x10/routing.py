"""Main project channels routing."""
from channels.routing import include

from core.routing import routes as core_routes


routes = [
    include(core_routes),
]
