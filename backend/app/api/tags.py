import uuid
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.auth.guards import require_event_member
from app.config import settings
from app.db.queries.invitations import get_membership
from app.db.queries.tags import get_own_tag_with_event, get_pending_tags_for_user, set_tag_review_status
from app.dependencies import CurrentUser, SessionDep
from app.schemas.tags import PendingTag, PendingTagsResponse, TagReviewResponse
from app.storage.client import storage_client

log = structlog.get_logger()

router = APIRouter(tags=["tags"])


@router.get(
    "/events/{event_id}/pending-tags/mine",
    response_model=PendingTagsResponse,
    dependencies=[Depends(require_event_member)],
)
async def get_pending_tags_endpoint(
    event_id: uuid.UUID,
    session: SessionDep,
    user_id: CurrentUser,
):
    structlog.contextvars.bind_contextvars(event_id=str(event_id))
    pending = await get_pending_tags_for_user(session, event_id, user_id)

    # Face crop if the tag's face has one, otherwise the photo's thumbnail —
    # one batch signing call either way.
    keys = [tag.crop_key or tag.thumb_key for tag in pending]
    try:
        signed = await run_in_threadpool(
            storage_client.create_signed_read_urls, keys, settings.gallery_url_expires_in
        )
    except Exception:
        log.exception("tags.pending.signed_url_failed", count=len(pending))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not load pending tags, try again",
        ) from None

    response = PendingTagsResponse(
        tags=[
            PendingTag(
                photo_id=tag.photo_id,
                similarity=tag.similarity,
                crop_url=signed[tag.crop_key or tag.thumb_key],
            )
            for tag in pending
        ]
    )
    log.info("tags.pending.listed", count=len(response.tags))
    return response


async def _review_tag(
    photo_id: uuid.UUID,
    session: SessionDep,
    user_id: CurrentUser,
    *,
    new_status: Literal["confirmed", "rejected"],
    new_source: Literal["guest_confirmed"] | None,
) -> TagReviewResponse:
    # No event_id in this route, so membership can't be checked via the
    # require_event_member dependency (it needs an event_id path param) —
    # derive it from the tag's photo instead.
    found = await get_own_tag_with_event(session, photo_id, user_id)
    if found is None:
        # Covers both "no such tag" and "this tag belongs to someone else":
        # scoping the lookup to user_id makes those indistinguishable on
        # purpose, same as the photo-not-found pattern in app/api/photos.py.
        log.info("tags.review.not_found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    tag, event_id = found
    structlog.contextvars.bind_contextvars(event_id=str(event_id))

    membership = await get_membership(session, event_id, user_id)
    if membership is None:
        log.info("tags.review.not_a_member")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this event")

    tag = await set_tag_review_status(session, tag, status=new_status, source=new_source)
    log.info("tags.review.updated", status=tag.status, source=tag.source)
    return TagReviewResponse(photo_id=tag.photo_id, status=tag.status, source=tag.source)


@router.post("/tags/{photo_id}/confirm", response_model=TagReviewResponse)
async def confirm_tag_endpoint(
    photo_id: uuid.UUID,
    session: SessionDep,
    user_id: CurrentUser,
):
    structlog.contextvars.bind_contextvars(photo_id=str(photo_id))
    log.info("tags.review.confirm_requested")
    return await _review_tag(
        photo_id, session, user_id, new_status="confirmed", new_source="guest_confirmed"
    )


@router.post("/tags/{photo_id}/reject", response_model=TagReviewResponse)
async def reject_tag_endpoint(
    photo_id: uuid.UUID,
    session: SessionDep,
    user_id: CurrentUser,
):
    structlog.contextvars.bind_contextvars(photo_id=str(photo_id))
    log.info("tags.review.reject_requested")
    return await _review_tag(photo_id, session, user_id, new_status="rejected", new_source=None)
