import uuid

import structlog
from fastapi import APIRouter, Depends, status
from fastapi.concurrency import run_in_threadpool

from app.auth.guards import require_event_member, require_host
from app.db.queries.events import create_event, delete_event, get_event, list_events_by_host
from app.dependencies import CurrentUser, SessionDep
from app.schemas.events import EventCreate, EventRead
from app.storage.client import storage_client
from app.storage.keys import event_prefix

log = structlog.get_logger()

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event_endpoint(
    body: EventCreate,
    session: SessionDep,
    user_id: CurrentUser,
):
    event = await create_event(
        session,
        host_id=user_id,
        name=body.name,
        event_date=body.event_date,
        expires_at=body.expires_at,
    )
    structlog.contextvars.bind_contextvars(event_id=str(event.id))
    log.info("event.created", expires_at=event.expires_at.isoformat())
    return event


@router.get("", response_model=list[EventRead])
async def list_events_endpoint(
    session: SessionDep,
    user_id: CurrentUser,
):
    return await list_events_by_host(session, user_id)


@router.get(
    "/{event_id}",
    response_model=EventRead,
    dependencies=[Depends(require_event_member)],
)
async def get_event_endpoint(
    event_id: uuid.UUID,
    session: SessionDep,
):
    return await get_event(session, event_id)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_host)],
)
async def delete_event_endpoint(
    event_id: uuid.UUID,
    session: SessionDep,
):
    structlog.contextvars.bind_contextvars(event_id=str(event_id))
    log.info("event.delete.requested")

    event = await get_event(session, event_id)

    # Storage first: if this fails, the DB row (and thus the host's ability
    # to retry) survives. Deleting the DB row first and then failing the
    # storage purge would strand biometric data with nothing pointing at it.
    prefix = event_prefix(event_id)
    purged_count = await run_in_threadpool(storage_client.delete_prefix, prefix)
    log.info("event.storage.purged", prefix=prefix, count=purged_count)

    await delete_event(session, event)
    log.info("event.deleted")
