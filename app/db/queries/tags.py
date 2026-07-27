import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.face import Face
from app.models.photo_tag import PhotoTag


@dataclass
class EnrollmentMatch:
    user_id: uuid.UUID
    similarity: float


@dataclass
class TagUpsert:
    photo_id: uuid.UUID
    user_id: uuid.UUID
    face_id: uuid.UUID
    similarity: float


def _vector_literal(embedding: Sequence[float]) -> str:
    # pgvector's text input format: '[v1,v2,...]'. Built explicitly here
    # rather than relying on pgvector.sqlalchemy's bind processor, since this
    # is a raw SQL query with no ORM column to attach a type to.
    return "[" + ",".join(str(float(v)) for v in embedding) + "]"


_TOP_ENROLLMENT_MATCHES_SQL = text(
    """
    SELECT user_id, 1 - (embedding <=> CAST(:face_vec AS vector)) AS similarity
    FROM face_enrollments
    WHERE event_id = :event_id
    ORDER BY embedding <=> CAST(:face_vec AS vector)
    LIMIT 2
    """
)


async def find_top_enrollment_matches(
    session: AsyncSession, event_id: uuid.UUID, face_embedding: Sequence[float]
) -> list[EnrollmentMatch]:
    """Top-2 nearest enrollments to a face embedding, scoped to one event.

    Returns 2 rather than 1 so a future margin test (Phase 11: is the winner
    convincingly closer than the runner-up, not just above a single cutoff)
    can be added without changing this query. For now, callers only use the
    top result.
    """
    result = await session.execute(
        _TOP_ENROLLMENT_MATCHES_SQL,
        {"face_vec": _vector_literal(face_embedding), "event_id": event_id},
    )
    return [EnrollmentMatch(user_id=row.user_id, similarity=row.similarity) for row in result.all()]


async def match_faces_to_enrollments(
    session: AsyncSession,
    event_id: uuid.UUID,
    photo_id: uuid.UUID,
    faces: list[Face],
) -> list[TagUpsert]:
    """For each detected face, find its nearest enrollment and keep it if the
    similarity clears settings.match_threshold. One DB round trip per face —
    fine at photo-processing volume (a handful of faces per photo)."""
    tags = []
    for face in faces:
        if face.embedding is None:
            continue

        top_matches = await find_top_enrollment_matches(session, event_id, face.embedding)
        if not top_matches:
            continue

        best = top_matches[0]
        if best.similarity >= settings.match_threshold:
            tags.append(
                TagUpsert(
                    photo_id=photo_id,
                    user_id=best.user_id,
                    face_id=face.id,
                    similarity=best.similarity,
                )
            )
    return tags


async def upsert_tags(session: AsyncSession, tags: list[TagUpsert]) -> None:
    """Insert tag rows, skipping any that collide on (photo_id, user_id).

    ON CONFLICT DO NOTHING at the database level means a user matched by two
    different faces in the same photo still ends up with one tag row, and
    re-running this for a photo (retry, reprocessing) never duplicates or
    errors on tags that already exist.
    """
    if not tags:
        return

    stmt = (
        pg_insert(PhotoTag)
        .values(
            [
                {
                    "photo_id": tag.photo_id,
                    "user_id": tag.user_id,
                    "face_id": tag.face_id,
                    "similarity": tag.similarity,
                }
                for tag in tags
            ]
        )
        .on_conflict_do_nothing(index_elements=["photo_id", "user_id"])
    )
    await session.execute(stmt)
    await session.commit()
