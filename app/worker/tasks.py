import asyncio
import uuid

import structlog

from app.db.queries.photos import get_photo, mark_photo_processed
from app.db.session import async_session_factory
from app.worker.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3)
def process_photo(self, photo_id: str) -> None:
    # Sync task boundary, single asyncio.run() wrapping the async DB work
    # rather than event loops scattered through the task body.
    asyncio.run(_process_photo(photo_id))


async def _process_photo(photo_id: str) -> None:
    structlog.contextvars.bind_contextvars(photo_id=photo_id)
    log.info("photo.processing.started")

    try:
        async with async_session_factory() as session:
            photo = await get_photo(session, uuid.UUID(photo_id))
            if photo is None:
                log.warning("photo.processing.not_found")
                return

            structlog.contextvars.bind_contextvars(event_id=str(photo.event_id))

            # TODO(Phase 5): detect faces, compute embeddings, and match
            # against this event's guest enrollments.
            await mark_photo_processed(session, photo)
            log.info("photo.processing.completed", status=photo.status)
    finally:
        structlog.contextvars.clear_contextvars()


@celery_app.task(bind=True, max_retries=3)
def purge_expired_data(self) -> None:
    log.info("maintenance.purge.started")
    # TODO: delete expired biometric data (embeddings, selfies, face crops)
    # per each event's retention policy.
    log.info("maintenance.purge.completed")


@celery_app.task(bind=True, max_retries=3)
def reconcile_orphaned_uploads(self) -> None:
    log.info("maintenance.reconcile_orphaned_uploads.started")
    # TODO: find photos stuck in 'awaiting_upload' older than one hour
    # (client never confirmed the upload) and mark them failed.
    log.info("maintenance.reconcile_orphaned_uploads.completed")
