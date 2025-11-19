
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from decouple import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev' if config('DEBUG', default=False, cast=bool) else 'config.settings.prod')

app = Celery('reachvault')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
