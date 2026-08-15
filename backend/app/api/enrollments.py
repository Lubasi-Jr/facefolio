import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.auth.guards import require_event_member
from app.cv.detector import detect_faces
from app.cv.embedder import normalize_face_embedding
from app.cv.imaging import load_bgr
from app.cv.quality import validate_selfie
from app.db.queries.enrollments import upsert_enrollment
from app.db.queries.tags import TagUpsert, match_enrollment_to_faces, upsert_tags
from app.dependencies import CurrentUser, SessionDep
from app.schemas.enrollments import EnrollRequest, EnrollResponse, PrepareEnrollmentResponse
from app.storage.client import storage_client
from app.storage.keys import enrollment_selfie_key

log = structlog.get_logger()

router = APIRouter(tags=["enrollments"])


@router.post(
    "/events/{event_id}/enrollments/prepare",
    response_model=PrepareEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_event_member)],
)
async def prepare_enrollment_endpoint(
    event_id: uuid.UUID,
    user_id: CurrentUser,
):
    structlog.contextvars.bind_contextvars(event_id=str(event_id))
    log.info("enrollment.upload.prepare_requested")

    # Deterministic key (one enrollment per guest per event), so unlike
    # photos there's no id to mint and no row to pre-create here.
    key = enrollment_selfie_key(event_id, user_id)

    try:
        signed = await run_in_threadpool(storage_client.create_signed_upload_url, key, upsert=True)
    except Exception:
        log.exception("enrollment.upload.signed_url_failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not prepare upload, try again",
        ) from None

    log.info("enrollment.upload.prepared")
    return PrepareEnrollmentResponse(selfie_key=key, upload_url=signed["signed_url"])


@router.post(
    "/events/{event_id}/enroll",
    response_model=EnrollResponse,
    dependencies=[Depends(require_event_member)],
)
async def enroll_endpoint(
    event_id: uuid.UUID,
    body: EnrollRequest,
    session: SessionDep,
    user_id: CurrentUser,
):
    structlog.contextvars.bind_contextvars(event_id=str(event_id), user_id=str(user_id))
    log.info("enrollment.requested")

    if not body.consent:
        log.info("enrollment.consent_rejected")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Consent is required to enroll",
        )

    with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        try:
            await run_in_threadpool(storage_client.download_to_path, body.selfie_key, tmp_path)
        except Exception:
            log.exception("enrollment.download_failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not read the uploaded selfie, try again",
            ) from None

        # This runs synchronously in the request (not a Celery task): the
        # guest is waiting on the result to see which photos matched, so
        # there's no queue message to defer the CV work to.
        image = load_bgr(tmp_path)

        quality = validate_selfie(image)
        if not quality.ok:
            log.info("enrollment.selfie_rejected", reason=quality.reason)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=quality.reason)

        # validate_selfie() already confirmed exactly one face; detect_faces()
        # is called again here to get its embedding, which validate_selfie()
        # doesn't expose.
        detection = detect_faces(image)[0]
        embedding = normalize_face_embedding(detection.embedding).tolist()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    enrollment = await upsert_enrollment(
        session,
        event_id=event_id,
        user_id=user_id,
        selfie_key=body.selfie_key,
        embedding=embedding,
        quality_score=detection.det_score,
        consented_at=datetime.now(timezone.utc),
    )
    log.info("enrollment.created", quality_score=round(enrollment.quality_score, 3))

    matches = await match_enrollment_to_faces(session, event_id, embedding)
    # face_id is left unset: this match is against photos, not a specific
    # face row (see TagUpsert). source/status take the photo_tags column
    # defaults, which are "auto" and "confirmed".
    tags = [
        TagUpsert(photo_id=match.photo_id, user_id=user_id, similarity=match.similarity)
        for match in matches
    ]
    await upsert_tags(session, tags)
    log.info("enrollment.matched", count=len(matches))

    return EnrollResponse(
        matched_count=len(matches),
        matched_photo_ids=[match.photo_id for match in matches],
    )
