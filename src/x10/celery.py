"""App-level config for Celery."""
from __future__ import absolute_import

import os

from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'x10.settings')

app = Celery('x10')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
