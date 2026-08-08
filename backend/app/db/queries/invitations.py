import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation


async def create_guest_invitation(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    email: str | None,
) -> Invitation:
    invitation = Invitation(
        event_id=event_id,
        invite_token=secrets.token_urlsafe(24),
        email=email,
        role="guest",
        status="pending",
    )
    session.add(invitation)
    await session.commit()
    return invitation


async def get_invitation_by_token(session: AsyncSession, invite_token: str) -> Invitation | None:
    stmt = select(Invitation).where(Invitation.invite_token == invite_token)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def claim_invitation(
    session: AsyncSession,
    shared_invitation: Invitation,
    user_id: uuid.UUID,
) -> Invitation:
    # The shared invitation (the QR-coded link) is never mutated — it stays
    # pending so other guests can still claim it. Claiming inserts a new,
    # personal membership row instead (see docs/FLOWS.md Flow 4a).
    membership = Invitation(
        event_id=shared_invitation.event_id,
        invite_token=secrets.token_urlsafe(24),
        user_id=user_id,
        role=shared_invitation.role,
        status="joined",
    )
    session.add(membership)
    await session.commit()
    return membership


async def get_membership(
    session: AsyncSession,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Invitation | None:
    stmt = select(Invitation).where(
        Invitation.event_id == event_id,
        Invitation.user_id == user_id,
        Invitation.status == "joined",
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
