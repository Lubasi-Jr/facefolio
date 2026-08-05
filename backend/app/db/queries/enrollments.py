import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face_enrollment import FaceEnrollment


async def upsert_enrollment(
    session: AsyncSession,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    selfie_key: str,
    embedding: Sequence[float],
    quality_score: float,
    consented_at: datetime,
) -> FaceEnrollment:
    """Create or replace a guest's enrollment selfie for an event.

    A guest may re-enroll (retake their selfie), so this upserts on the
    (event_id, user_id) unique constraint rather than erroring on conflict.
    """
    stmt = (
        pg_insert(FaceEnrollment)
        .values(
            event_id=event_id,
            user_id=user_id,
            selfie_key=selfie_key,
            embedding=embedding,
            quality_score=quality_score,
            consented_at=consented_at,
        )
        .on_conflict_do_update(
            constraint="uq_face_enrollments_event_user",
            set_={
                "selfie_key": selfie_key,
                "embedding": embedding,
                "quality_score": quality_score,
                "consented_at": consented_at,
            },
        )
        .returning(FaceEnrollment)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()


async def get_event_enrollments(
    session: AsyncSession, event_id: uuid.UUID
) -> list[tuple[uuid.UUID, list[float]]]:
    # (user_id, embedding) pairs only — matching scans these per photo face
    # and has no use for selfie_key/quality_score/consented_at.
    stmt = select(FaceEnrollment.user_id, FaceEnrollment.embedding).where(
        FaceEnrollment.event_id == event_id
    )
    result = await session.execute(stmt)
    return [(user_id, embedding) for user_id, embedding in result.all()]
