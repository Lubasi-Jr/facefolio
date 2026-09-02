import asyncio
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.cv.detector import detect_faces
from app.cv.embedder import normalize_face_embedding
from app.cv.imaging import build_thumbnail, build_web_derivative, load_bgr
from app.cv.quality import is_face_usable
from app.db.queries.enrollments import get_event_enrollments
from app.db.queries.faces import FaceInsert, delete_faces_for_photo, insert_faces
from app.db.queries.photos import get_photo, mark_photo_failed, mark_photo_processed
from app.db.queries.purge import (
    find_expired_events,
    mark_event_purged,
    purge_event_biometrics_db,
    write_deletion_log,
)
from app.db.queries.tags import match_faces_to_enrollments, upsert_tags
from app.db.session import create_worker_engine
from app.models.photo import Photo
from app.storage.client import storage_client
from app.storage.keys import enrollment_prefix, thumb_key, web_key
from app.utils.exif import read_taken_at
from app.worker.celery_app import celery_app

log = structlog.get_logger()

# What purge_expired_data destroys: the face_enrollments row (selfie
# reference + embedding), the embedding vector itself (also nulled on
# faces), and the enrollment selfie object in storage. Recorded in
# deletion_log, never the biometric content it describes.
_PURGED_CATEGORIES = ["enrollments", "embeddings", "selfies"]

# Storage delete_prefix + re-list confirmation loop, distinct from Celery's
# task-level retry: Phase A has already committed by the time Phase B runs,
# so a transient storage failure retries in place first rather than
# immediately failing the whole task (which would just redo Phase A, harmless
# but wasteful).
_STORAGE_DELETE_MAX_ATTEMPTS = 3
_STORAGE_DELETE_RETRY_SECONDS = 2


@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True)
def process_photo(self, photo_id: str) -> None:
    # Sync task boundary, single asyncio.run() wrapping the async DB work
    # rather than event loops scattered through the task body.
    asyncio.run(_process_photo(photo_id))


async def _process_photo(photo_id: str) -> None:
    structlog.contextvars.bind_contextvars(photo_id=photo_id)
    log.info("photo.processing.started")

    # Engine is created here, inside the coroutine asyncio.run() is driving,
    # so its connections belong to *this* task's event loop. Disposed before
    # we return, so nothing survives for a later task's loop to collide with.
    engine, session_factory = create_worker_engine()
    try:
        async with session_factory() as session:
            photo = await get_photo(session, uuid.UUID(photo_id))
            if photo is None:
                log.warning("photo.processing.not_found")
                return

            structlog.contextvars.bind_contextvars(event_id=str(photo.event_id))

            try:
                await _run_pipeline(session, photo)
                log.info("photo.processing.completed", status=photo.status)
            except Exception:
                log.exception("photo.processing.failed")
                # The failed step may have left the transaction aborted;
                # roll back before writing the failure status in a fresh one.
                await session.rollback()
                await mark_photo_failed(session, photo)
                raise
    finally:
        await engine.dispose()
        structlog.contextvars.clear_contextvars()


def _bbox_to_xywh(bbox: np.ndarray) -> list[int]:
    x1, y1, x2, y2 = bbox
    return [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]


async def _run_pipeline(session: AsyncSession, photo: Photo) -> None:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        storage_client.download_to_path(photo.original_key, tmp_path)

        web_bytes = build_web_derivative(tmp_path)
        thumb_bytes = build_thumbnail(tmp_path)
        new_web_key = web_key(photo.event_id, photo.id)
        new_thumb_key = thumb_key(photo.event_id, photo.id)
        storage_client.upload_bytes(new_web_key, web_bytes, content_type="image/webp")
        storage_client.upload_bytes(new_thumb_key, thumb_bytes, content_type="image/webp")
        log.info(
            "photo.processing.derivatives_built",
            web_bytes=len(web_bytes),
            thumb_bytes=len(thumb_bytes),
        )

        image = load_bgr(tmp_path)
        detections = detect_faces(image)
        log.info(
            "photo.processing.faces_detected",
            face_count=len(detections),
            det_scores=[round(d.det_score, 3) for d in detections],
        )

        usable_detections = []
        reject_reasons: dict[str, int] = {}
        for detection in detections:
            quality = is_face_usable(image, detection.bbox, detection.det_score)
            if quality.ok:
                usable_detections.append(detection)
            else:
                reject_reasons[quality.reason] = reject_reasons.get(quality.reason, 0) + 1
        log.info(
            "photo.processing.quality_gated",
            passed=len(usable_detections),
            rejected=len(detections) - len(usable_detections),
            reject_reasons=reject_reasons,
        )

        face_inserts = [
            FaceInsert(
                bbox=_bbox_to_xywh(detection.bbox),
                det_score=detection.det_score,
                embedding=normalize_face_embedding(detection.embedding),
            )
            for detection in usable_detections
        ]

        await delete_faces_for_photo(session, photo.id)
        faces = await insert_faces(session, photo.id, photo.event_id, face_inserts)
        log.info("photo.processing.faces_stored", face_count=len(faces))

        if faces:
            enrollments = await get_event_enrollments(session, photo.event_id)
            if enrollments:
                tags = await match_faces_to_enrollments(session, photo.event_id, photo.id, faces)
                await upsert_tags(session, tags)
                log.info(
                    "photo.processing.tags_matched",
                    face_count=len(faces),
                    enrollment_count=len(enrollments),
                    tag_count=len(tags),
                    similarities=[round(tag.similarity, 3) for tag in tags],
                )
            else:
                log.info("photo.processing.no_enrollments")

        taken_at = read_taken_at(tmp_path)
        await mark_photo_processed(
            session,
            photo,
            web_key=new_web_key,
            thumb_key=new_thumb_key,
            taken_at=taken_at,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True)
def purge_expired_data(self, dry_run: bool = False) -> None:
    # Sync task boundary, single asyncio.run() wrapping the async DB work —
    # same shape as process_photo above.
    asyncio.run(_purge_expired_data(dry_run=dry_run))


async def _purge_expired_data(dry_run: bool) -> None:
    log.info("maintenance.purge.started", dry_run=dry_run)

    engine, session_factory = create_worker_engine()
    try:
        async with session_factory() as session:
            events = await find_expired_events(session)
            log.info(
                "maintenance.purge.candidates_found",
                count=len(events),
                event_ids=[str(event.id) for event in events],
                dry_run=dry_run,
            )

            if dry_run:
                # No mutation at all — this is purely so the selection can be
                # eyeballed (event_ids above) before any deletion runs live.
                log.info("maintenance.purge.dry_run_complete", would_purge_count=len(events))
                return

            purged_count = 0
            failed_event_ids: list[str] = []
            for event in events:
                try:
                    await _purge_one_event(session, event.id)
                    purged_count += 1
                except Exception:
                    failed_event_ids.append(str(event.id))
                    log.exception("maintenance.purge.event_failed", event_id=str(event.id))
                finally:
                    structlog.contextvars.unbind_contextvars("event_id")

            log.info(
                "maintenance.purge.completed",
                purged_count=purged_count,
                failed_count=len(failed_event_ids),
                failed_event_ids=failed_event_ids,
            )
            if failed_event_ids:
                # Raise so Celery's autoretry re-runs the batch. Every step
                # below is idempotent and find_expired_events excludes events
                # already marked 'purged', so the retry only redoes the
                # events that actually failed.
                raise RuntimeError(f"purge failed for {len(failed_event_ids)} event(s)")
    finally:
        await engine.dispose()
        structlog.contextvars.clear_contextvars()


async def _purge_one_event(session: AsyncSession, event_id: uuid.UUID) -> None:
    structlog.contextvars.bind_contextvars(event_id=str(event_id))

    # Phase A first: the DB transaction makes biometric data unusable to any
    # query (matching, gallery, exports) immediately, even if the storage
    # delete below is slow or has to retry.
    await purge_event_biometrics_db(session, event_id)
    db_purged_at = datetime.now(UTC)
    log.info("maintenance.purge.db_purged", event_id=str(event_id))

    # Phase B: only the enrollments/ prefix. Never originals/, web/, or
    # thumbs/ — those are the non-biometric event photos guests still expect
    # to see. (Face crops are never stored today — every faces.crop_key is
    # null, which is why Phase A nulls it defensively — so there is no
    # faces/ prefix to delete here; if crop storage is added later, extend
    # this to also purge events/{id}/faces/.)
    prefix = enrollment_prefix(event_id)
    deleted_count = _delete_prefix_confirmed(prefix)
    storage_purged_at = datetime.now(UTC)
    log.info(
        "maintenance.purge.storage_purged",
        event_id=str(event_id),
        deleted_count=deleted_count,
    )

    await mark_event_purged(session, event_id)
    await write_deletion_log(
        session,
        event_id=event_id,
        categories=_PURGED_CATEGORIES,
        db_purged_at=db_purged_at,
        storage_purged_at=storage_purged_at,
    )
    log.info("maintenance.purge.event_completed", event_id=str(event_id))


def _delete_prefix_confirmed(prefix: str) -> int:
    """Deletes a storage prefix, retrying until a re-list confirms it's
    empty. Raises if it still isn't after all attempts, so the caller never
    reports storage_purged_at for a prefix that might not actually be empty.
    """
    deleted_count = 0
    for attempt in range(1, _STORAGE_DELETE_MAX_ATTEMPTS + 1):
        deleted_count = storage_client.delete_prefix(prefix)
        if storage_client.prefix_is_empty(prefix):
            return deleted_count
        log.warning(
            "maintenance.purge.storage_delete_unconfirmed",
            prefix=prefix,
            attempt=attempt,
        )
        if attempt < _STORAGE_DELETE_MAX_ATTEMPTS:
            time.sleep(_STORAGE_DELETE_RETRY_SECONDS * attempt)
    raise RuntimeError(
        f"storage prefix not confirmed empty after {_STORAGE_DELETE_MAX_ATTEMPTS} attempts: {prefix}"
    )


@celery_app.task(bind=True, max_retries=3)
def reconcile_orphaned_uploads(self) -> None:
    log.info("maintenance.reconcile_orphaned_uploads.started")
    # TODO: find photos stuck in 'awaiting_upload' older than one hour
    # (client never confirmed the upload) and mark them failed.
    log.info("maintenance.reconcile_orphaned_uploads.completed")
