import uuid

from fastapi import HTTPException, status

from app.db.queries.invitations import get_membership
from app.dependencies import CurrentUser, SessionDep


async def require_event_member(
    event_id: uuid.UUID,
    session: SessionDep,
    user_id: CurrentUser,
) -> None:
    membership = await get_membership(session, event_id, user_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this event",
        )


async def require_host(
    event_id: uuid.UUID,
    session: SessionDep,
    user_id: CurrentUser,
) -> None:
    membership = await get_membership(session, event_id, user_id)
    if membership is None or membership.role != "host":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not the host of this event",
        )
