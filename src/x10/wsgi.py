"""WSGI config for main project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "x10.settings")

application = get_wsgi_application()
