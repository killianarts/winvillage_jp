import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "winvillage.settings")

app = Celery("winvillage")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
app.conf.broker_pool_limit = 1
app.conf.broker_heartbeat = None
app.conf.broker_connection_timeout = 30
app.conf.worker_prefetch_multiplier = 1
app.conf.result_backend = "django-db"
