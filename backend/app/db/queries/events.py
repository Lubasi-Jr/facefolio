import secrets
import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.invitation import Invitation


async def create_event(
    session: AsyncSession,
    *,
    host_id: uuid.UUID,
    name: str,
    event_date: date | None,
    expires_at: datetime,
) -> Event:
    event = Event(host_id=host_id, name=name, event_date=event_date, expires_at=expires_at)
    session.add(event)
    await session.flush()

    # Every membership, including the host's own, is an invitation row
    # (see docs/FLOWS.md) — this is what lets the auth guards later
    # confirm the host may manage this event.
    session.add(
        Invitation(
            event_id=event.id,
            invite_token=secrets.token_urlsafe(24),
            user_id=host_id,
            role="host",
            status="joined",
        )
    )
    await session.commit()
    return event


async def get_event(session: AsyncSession, event_id: uuid.UUID) -> Event | None:
    return await session.get(Event, event_id)


async def list_events_by_host(session: AsyncSession, host_id: uuid.UUID) -> list[Event]:
    stmt = select(Event).where(Event.host_id == host_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())
