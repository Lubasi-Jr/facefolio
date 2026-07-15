from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.supabase import verify_token
from app.db.queries.users import get_or_create_user
from app.db.session import get_session

bearer_scheme = HTTPBearer()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    session: SessionDep,
) -> UUID:
    user_id, email = verify_token(credentials.credentials)
    # The JWT carries no display name; fall back to the email's local part
    # until there's a "set your name" flow.
    user = await get_or_create_user(session, user_id, email, display_name=email.split("@")[0])
    return user.id


CurrentUser = Annotated[UUID, Depends(current_user)]
