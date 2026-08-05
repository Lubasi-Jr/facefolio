"""Celery beat schedule: periodic maintenance tasks.

Imported by celery_app's `include` so both the worker and beat processes
see it when the app finalizes; only the beat process actually acts on
beat_schedule.
"""

from celery.schedules import crontab

from app.worker.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "purge-expired-data": {
        "task": "app.worker.tasks.purge_expired_data",
        "schedule": crontab(hour=3, minute=0),  # daily at 03:00 UTC
    },
    "reconcile-orphaned-uploads": {
        "task": "app.worker.tasks.reconcile_orphaned_uploads",
        "schedule": crontab(minute=0),  # hourly, on the hour
    },
}
