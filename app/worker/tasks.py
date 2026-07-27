import asyncio
import tempfile
import uuid
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
from app.db.queries.tags import match_faces_to_enrollments, upsert_tags
from app.db.session import async_session_factory
from app.models.photo import Photo
from app.storage.client import storage_client
from app.storage.keys import thumb_key, web_key
from app.utils.exif import read_taken_at
from app.worker.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True)
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
