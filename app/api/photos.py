import asyncio
import time
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.auth.guards import require_event_member, require_host
from app.config import settings
from app.db.queries.photos import (
    count_photos_by_status,
    count_photos_for_event,
    create_photos,
    get_gallery_photos,
    get_photo,
    mark_photo_queued,
)
from app.dependencies import CurrentUser, SessionDep
from app.schemas.photos import (
    GalleryPhoto,
    GalleryResponse,
    PhotoConfirmResponse,
    PreparedPhotoUpload,
    PreparePhotosRequest,
    PreparePhotosResponse,
    ProcessingStatusResponse,
)
from app.storage.client import storage_client
from app.storage.keys import original_key

log = structlog.get_logger()

router = APIRouter(tags=["photos"])


@router.post(
    "/events/{event_id}/photos/prepare",
    response_model=PreparePhotosResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_host)],
)
async def prepare_photos_endpoint(
    event_id: uuid.UUID,
    body: PreparePhotosRequest,
    session: SessionDep,
    user_id: CurrentUser,
):
    structlog.contextvars.bind_contextvars(event_id=str(event_id))
    requested_count = len(body.photos)
    log.info("photo.upload.prepare_requested", count=requested_count)
    start = time.perf_counter()

    existing_count = await count_photos_for_event(session, event_id)
    if existing_count + requested_count > settings.max_photos_per_event:
        log.info(
            "photo.upload.cap_exceeded",
            existing_count=existing_count,
            requested_count=requested_count,
            cap=settings.max_photos_per_event,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This would exceed the event's {settings.max_photos_per_event}-photo limit",
        )

    photo_ids = [uuid.uuid4() for _ in body.photos]
    keys = [original_key(event_id, photo_id) for photo_id in photo_ids]

    try:
        signed_urls = await asyncio.gather(
            *(run_in_threadpool(storage_client.create_signed_upload_url, key) for key in keys)
        )
    except Exception:
        log.exception("photo.upload.signed_url_failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not prepare uploads, try again",
        ) from None

    await create_photos(
        session,
        event_id=event_id,
        uploader_id=user_id,
        photos=list(zip(photo_ids, keys)),
    )

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    log.info("photo.upload.prepared", count=requested_count, duration_ms=duration_ms)

    return PreparePhotosResponse(
        photos=[
            PreparedPhotoUpload(photo_id=photo_id, upload_url=signed["signed_url"])
            for photo_id, signed in zip(photo_ids, signed_urls)
        ]
    )


@router.post(
    "/events/{event_id}/photos/{photo_id}/confirm",
    response_model=PhotoConfirmResponse,
    dependencies=[Depends(require_host)],
)
async def confirm_photo_endpoint(
    event_id: uuid.UUID,
    photo_id: uuid.UUID,
    session: SessionDep,
):
    structlog.contextvars.bind_contextvars(event_id=str(event_id), photo_id=str(photo_id))
    log.info("photo.upload.confirm_requested")

    photo = await get_photo(session, photo_id)
    if photo is None or photo.event_id != event_id:
        # Same response either way: a photo id from another event must not
        # be distinguishable from one that doesn't exist at all.
        log.info("photo.upload.confirm_not_found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    if photo.status != "awaiting_upload":
        log.info("photo.upload.confirm_rejected", status=photo.status)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Photo is '{photo.status}', expected 'awaiting_upload'",
        )

    from_status = photo.status
    photo = await mark_photo_queued(session, photo)
    log.info("photo.upload.confirmed", from_status=from_status, to_status=photo.status)

    # TODO(Phase 4): enqueue the Celery task that detects faces and computes
    # embeddings for this photo, carrying only photo_id per the queue-message
    # convention in CLAUDE.md.
    log.info("photo.upload.enqueue_pending", note="Celery enqueue not yet implemented")

    return PhotoConfirmResponse(photo_id=photo.id, status=photo.status)


@router.get(
    "/events/{event_id}/processing-status",
    response_model=ProcessingStatusResponse,
    dependencies=[Depends(require_event_member)],
)
async def get_processing_status_endpoint(
    event_id: uuid.UUID,
    session: SessionDep,
):
    structlog.contextvars.bind_contextvars(event_id=str(event_id))
    counts = await count_photos_by_status(session, event_id)
    log.info("photo.processing.status_requested", **counts)
    return ProcessingStatusResponse(**counts)


@router.get(
    "/events/{event_id}/photos",
    response_model=GalleryResponse,
    dependencies=[Depends(require_event_member)],
)
async def get_gallery_endpoint(
    event_id: uuid.UUID,
    session: SessionDep,
):
    structlog.contextvars.bind_contextvars(event_id=str(event_id))
    photos = await get_gallery_photos(session, event_id)

    # web_key/thumb_key are guaranteed set by the get_gallery_photos filter.
    keys = [key for photo in photos for key in (photo.web_key, photo.thumb_key)]
    try:
        signed = await run_in_threadpool(
            storage_client.create_signed_read_urls, keys, settings.gallery_url_expires_in
        )
    except Exception:
        log.exception("photo.gallery.signed_url_failed", count=len(photos))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not load gallery, try again",
        ) from None

    gallery = [
        GalleryPhoto(
            photo_id=photo.id,
            web_url=signed[photo.web_key],
            thumb_url=signed[photo.thumb_key],
        )
        for photo in photos
    ]

    log.info("photo.gallery.listed", count=len(gallery))

    return GalleryResponse(photos=gallery)
