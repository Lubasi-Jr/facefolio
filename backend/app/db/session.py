from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

engine = create_async_engine(settings.database_url)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


def create_worker_engine() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Build a fresh engine + sessionmaker, scoped to a single Celery task run.

    Do NOT reuse the module-level `engine` above inside a Celery task. Each
    task is invoked via asyncio.run(), which creates and later closes its own
    event loop; asyncpg connections (and SQLAlchemy's async connection pool)
    are bound to the loop that created them, so a pooled connection from a
    previous task's now-closed loop is unsafe to reuse. Call this from inside
    the coroutine that asyncio.run() executes, and dispose the returned
    engine before that coroutine returns, so nothing outlives the loop.
    """
    worker_engine = create_async_engine(settings.database_url)
    worker_session_factory = async_sessionmaker(worker_engine, expire_on_commit=False)
    return worker_engine, worker_session_factory
