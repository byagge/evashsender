import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')

app = Celery('vashsender')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Configure Celery settings
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    broker_connection_retry_on_startup=True,
    result_expires=3600,  # 1 hour
)

# Configure task routes
app.conf.task_routes = {
    'apps.campaigns.tasks.*': {'queue': 'email'},
    'apps.campaigns.tasks.send_campaign': {'queue': 'campaigns'},
    'apps.campaigns.tasks.send_email_batch': {'queue': 'email'},
}

# Configure task queues
app.conf.task_default_queue = 'default'
app.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'email': {
        'exchange': 'email',
        'routing_key': 'email',
        'queue_arguments': {'x-max-priority': 10},
    },
    'campaigns': {
        'exchange': 'campaigns',
        'routing_key': 'campaigns',
        'queue_arguments': {'x-max-priority': 10},
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 