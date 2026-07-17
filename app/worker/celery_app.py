import ssl

from celery import Celery
from celery.signals import worker_process_init

from app.config import settings
from app.logging_config import configure_logging

celery_app = Celery(
    "facefolio",
    broker=settings.redis_url,
    # Imported when the app finalizes so `celery -A app.worker.celery_app
    # worker`/`beat` register tasks and the beat schedule without anything
    # else in the process happening to import those modules first.
    include=["app.worker.tasks", "app.worker.scheduler"],
)

celery_app.conf.update(
    # No result backend: task outcomes are tracked via the photos.status
    # column in Postgres, which the frontend polls directly.
    result_backend=None,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=120,
    task_time_limit=150,
    task_default_retry_delay=5,
    task_annotations={"*": {"max_retries": 3}},
)

# Upstash (and most managed Redis) serve rediss:// with a cert chain that
# isn't in Python's default trust store, so we verify the connection but
# don't pin/require a client cert.
if settings.redis_url.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}


@worker_process_init.connect
def _configure_worker_logging(**kwargs) -> None:
    # Fires once per worker process on startup so worker logs use the same
    # structlog processors/renderer as the API instead of Celery's own format.
    configure_logging()
