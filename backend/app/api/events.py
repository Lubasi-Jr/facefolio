import uuid

import structlog
from fastapi import APIRouter, Depends, status

from app.auth.guards import require_event_member
from app.db.queries.events import create_event, get_event, list_events_by_host
from app.dependencies import CurrentUser, SessionDep
from app.schemas.events import EventCreate, EventRead

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
