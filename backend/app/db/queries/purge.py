import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.deletion_log import DeletionLog
from app.models.event import Event
from app.models.face import Face
from app.models.face_enrollment import FaceEnrollment
from app.models.photo import Photo
from app.models.photo_tag import PhotoTag


async def find_expired_events(session: AsyncSession) -> list[Event]:
    """Events whose grace period has elapsed and are not yet purged."""
    cutoff = datetime.now(UTC) - timedelta(days=settings.purge_grace_days)
    stmt = select(Event).where(Event.expires_at < cutoff, Event.status != "purged")
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def purge_event_biometrics_db(session: AsyncSession, event_id: uuid.UUID) -> None:
    """Phase A: strip biometric material from the DB for one event, in one transaction.

    Deletes face_enrollments outright (selfie + embedding) and nulls the
    embedding/crop_key columns on faces rows — the faces rows themselves stay,
    since bbox/det_score are non-biometric and the gallery still needs them.
    Idempotent: safe to re-run if a prior attempt crashed mid-transaction.
    """
    await session.execute(
        update(Event)
        .where(Event.id == event_id, Event.status != "expired")
        .values(status="expired")
    )
    await session.execute(delete(FaceEnrollment).where(FaceEnrollment.event_id == event_id))
    await session.execute(
        update(Face).where(Face.event_id == event_id).values(embedding=None, crop_key=None)
    )
    await session.commit()


async def purge_user_biometrics_db(
    session: AsyncSession, *, event_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Right-to-erasure DB step for one guest in one event, in one transaction.

    Nulls embedding/crop_key ONLY on the faces this guest was actually tagged
    in (via photo_tags.face_id) — not every face in photos they appear in,
    since other faces in those photos belong to other people. Then deletes
    this guest's photo_tags and their face_enrollments row. The event's
    photos, faces rows, and everyone else's tags/embeddings are untouched.

    Order matters: faces are nulled via the photo_tags join *before* those
    photo_tags rows are deleted, since that join is the only way to find
    which faces belong to this guest. Idempotent: re-running once everything
    is already gone is a no-op.
    """
    linked_face_ids = (
        select(PhotoTag.face_id)
        .join(Photo, Photo.id == PhotoTag.photo_id)
        .where(
            PhotoTag.user_id == user_id,
            Photo.event_id == event_id,
            PhotoTag.face_id.isnot(None),
        )
    )
    await session.execute(
        update(Face).where(Face.id.in_(linked_face_ids)).values(embedding=None, crop_key=None)
    )
    await session.execute(
        delete(PhotoTag).where(
            PhotoTag.user_id == user_id,
            PhotoTag.photo_id.in_(select(Photo.id).where(Photo.event_id == event_id)),
        )
    )
    await session.execute(
        delete(FaceEnrollment).where(
            FaceEnrollment.event_id == event_id, FaceEnrollment.user_id == user_id
        )
    )
    await session.commit()


async def mark_event_purged(session: AsyncSession, event_id: uuid.UUID) -> None:
    """Phase B follow-up: flag the event purged once storage cleanup has also succeeded."""
    await session.execute(update(Event).where(Event.id == event_id).values(status="purged"))
    await session.commit()


async def write_deletion_log(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    categories: list[str],
    db_purged_at: datetime,
    storage_purged_at: datetime,
) -> None:
    """Records that a purge happened for an event — never the biometric
    content itself."""
    session.add(
        DeletionLog(
            event_id=event_id,
            categories=categories,
            db_purged_at=db_purged_at,
            storage_purged_at=storage_purged_at,
        )
    )
    await session.commit()
