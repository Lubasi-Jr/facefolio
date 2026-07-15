import uuid

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_or_create_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    email: str,
    display_name: str,
) -> User:
    user = await session.get(User, user_id)
    if user is not None:
        return user

    # ON CONFLICT DO NOTHING: two concurrent requests for a brand-new user
    # could both miss the get() above and race to insert the same id.
    stmt = (
        pg_insert(User)
        .values(id=user_id, email=email, display_name=display_name)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.execute(stmt)
    await session.commit()

    return await session.get(User, user_id)
