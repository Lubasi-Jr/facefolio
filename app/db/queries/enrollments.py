import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face_enrollment import FaceEnrollment


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
