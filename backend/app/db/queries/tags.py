import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.face import Face
from app.models.photo import Photo
from app.models.photo_tag import PhotoTag

# 'none' means "no tag" (classify_match callers drop these, never insert a
# row). TagStatus is the subset that's actually valid to write to
# photo_tags.status.
MatchBand = Literal["confirmed", "pending_guest", "none"]
TagStatus = Literal["confirmed", "pending_guest"]


@dataclass
class EnrollmentMatch:
    user_id: uuid.UUID
    similarity: float


@dataclass
class FaceMatch:
    photo_id: uuid.UUID
    similarity: float


@dataclass
class TagUpsert:
    photo_id: uuid.UUID
    user_id: uuid.UUID
    similarity: float
    # None for tags produced by enrollment-time matching (see
    # match_enrollment_to_faces), which matches against photos, not a
    # specific face row. photo_tags.face_id is nullable for this reason.
    face_id: uuid.UUID | None = None
    status: TagStatus = "confirmed"


def classify_match(
    best_similarity: float,
    second_best_similarity: float | None,
    t_high: float,
    t_low: float,
    margin: float,
) -> MatchBand:
    """Bands a match by confidence. Pure function, no I/O — the only inputs
    are similarity scores and the three configured thresholds (settings.
    match_t_high / match_t_low / match_margin, calibrated via
    scripts/evaluate_thresholds.py), so this is unit-testable without a
    database or the CV model.

    - 'confirmed': best >= t_high, and either there's no runner-up to compare
      against or best clears it by at least `margin`. The margin test exists
      to catch lookalike guests: two enrolled guests who both score above
      t_high for the same face shouldn't be auto-resolved to whichever is
      marginally closer.
    - 'pending_guest': t_low <= best < t_high, OR best >= t_high but the
      margin test failed (a close call, not a clean miss) — either way, ask
      the guest to confirm rather than auto-tagging or dropping it.
    - 'none': best < t_low. Not a real candidate; produces no tag.

    A single enrolled guest (second_best_similarity is None) skips the margin
    test rather than being downgraded — there's no lookalike to disambiguate
    from.
    """
    if best_similarity < t_low:
        return "none"

    if best_similarity >= t_high:
        margin_ok = second_best_similarity is None or (best_similarity - second_best_similarity) >= margin
        return "confirmed" if margin_ok else "pending_guest"

    return "pending_guest"


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

    Returns 2 rather than 1 so classify_match's margin test (is the winner
    convincingly closer than the runner-up, not just above a single cutoff)
    can run without a second query.
    """
    result = await session.execute(
        _TOP_ENROLLMENT_MATCHES_SQL,
        {"face_vec": _vector_literal(face_embedding), "event_id": event_id},
    )
    return [EnrollmentMatch(user_id=row.user_id, similarity=row.similarity) for row in result.all()]


_BEST_FACE_MATCH_PER_PHOTO_SQL = text(
    """
    SELECT DISTINCT ON (f.photo_id)
           f.photo_id,
           1 - (f.embedding <=> CAST(:selfie_vec AS vector)) AS similarity
    FROM faces f
    WHERE f.event_id = :event_id
      AND f.embedding IS NOT NULL
      AND 1 - (f.embedding <=> CAST(:selfie_vec AS vector)) >= :threshold
    ORDER BY f.photo_id, f.embedding <=> CAST(:selfie_vec AS vector)
    """
)


async def match_enrollment_to_faces(
    session: AsyncSession,
    event_id: uuid.UUID,
    selfie_embedding: Sequence[float],
    threshold: float = settings.match_t_low,
) -> list[FaceMatch]:
    """For a guest's enrollment selfie, find their best-matching face in each
    event photo. DISTINCT ON (photo_id) keeps only the nearest face per photo,
    so a guest appearing twice in one photo still yields a single result for
    that photo. Faces with a NULL embedding (purged at event expiry) are
    excluded.

    `threshold` (default T_low) is only a floor to keep obviously-irrelevant
    rows out of the result set — anything below T_low would classify to
    'none' anyway. It is NOT the confirm/reject cutoff: callers band each
    returned similarity with classify_match() in Python, so a photo scoring
    between T_low and T_high comes back as 'pending_guest' instead of being
    silently dropped here.
    """
    result = await session.execute(
        _BEST_FACE_MATCH_PER_PHOTO_SQL,
        {
            "selfie_vec": _vector_literal(selfie_embedding),
            "event_id": event_id,
            "threshold": threshold,
        },
    )
    return [FaceMatch(photo_id=row.photo_id, similarity=row.similarity) for row in result.all()]


async def match_faces_to_enrollments(
    session: AsyncSession,
    event_id: uuid.UUID,
    photo_id: uuid.UUID,
    faces: list[Face],
) -> list[TagUpsert]:
    """For each detected face, find its nearest enrollment(s) and band the
    best one with classify_match(). Top-2 (find_top_enrollment_matches) is
    fetched per face specifically so the margin test can run here — this is
    the path where a face genuinely might be a strong match for two different
    enrolled guests (lookalikes), so the runner-up matters. 'none' bands are
    dropped; 'confirmed' and 'pending_guest' both produce a tag, distinguished
    by TagUpsert.status. One DB round trip per face — fine at photo-processing
    volume (a handful of faces per photo).
    """
    tags = []
    for face in faces:
        if face.embedding is None:
            continue

        top_matches = await find_top_enrollment_matches(session, event_id, face.embedding)
        if not top_matches:
            continue

        best = top_matches[0]
        second_best = top_matches[1].similarity if len(top_matches) > 1 else None
        band = classify_match(
            best.similarity, second_best, settings.match_t_high, settings.match_t_low, settings.match_margin
        )
        if band == "none":
            continue

        tags.append(
            TagUpsert(
                photo_id=photo_id,
                user_id=best.user_id,
                face_id=face.id,
                similarity=best.similarity,
                status=band,
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
                    "status": tag.status,
                }
                for tag in tags
            ]
        )
        .on_conflict_do_nothing(index_elements=["photo_id", "user_id"])
    )
    await session.execute(stmt)
    await session.commit()


@dataclass
class PendingTagMedia:
    photo_id: uuid.UUID
    similarity: float
    # Only set when the tag came from the worker's per-face matching (see
    # match_faces_to_enrollments) and that face has a stored crop. Tags from
    # enrollment-time matching (match_enrollment_to_faces) never have a
    # face_id, so crop_key is always None for those — the caller falls back
    # to thumb_key.
    crop_key: str | None
    thumb_key: str


async def get_pending_tags_for_user(
    session: AsyncSession, event_id: uuid.UUID, user_id: uuid.UUID
) -> list[PendingTagMedia]:
    """A guest's 'pending_guest' tags, newest photo first, joined with enough
    storage keys to render a review card (face crop if there is one, plus
    the photo's thumbnail as a fallback). Only photos that have finished
    processing are included — thumb_key is guaranteed set by this filter,
    same as get_my_photos/get_gallery_photos.
    """
    stmt = (
        select(
            PhotoTag.photo_id,
            PhotoTag.similarity,
            Face.crop_key,
            Photo.thumb_key,
        )
        .join(Photo, Photo.id == PhotoTag.photo_id)
        .outerjoin(Face, Face.id == PhotoTag.face_id)
        .where(
            PhotoTag.user_id == user_id,
            PhotoTag.status == "pending_guest",
            Photo.event_id == event_id,
            Photo.thumb_key.isnot(None),
        )
        .order_by(Photo.taken_at.desc(), Photo.created_at.desc())
    )
    result = await session.execute(stmt)
    return [
        PendingTagMedia(
            photo_id=row.photo_id,
            similarity=row.similarity,
            crop_key=row.crop_key,
            thumb_key=row.thumb_key,
        )
        for row in result.all()
    ]


async def get_own_tag_with_event(
    session: AsyncSession, photo_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[PhotoTag, uuid.UUID] | None:
    """The (photo_id, user_id) tag, plus its event_id via the photo join, so
    a caller with no event_id in scope (e.g. POST /tags/{photo_id}/confirm)
    can both find the tag and check event membership. Scoping the lookup to
    user_id doubles as the "tag must belong to the current guest" check —
    another guest's tag on the same photo is simply not found, same as one
    that doesn't exist.
    """
    stmt = (
        select(PhotoTag, Photo.event_id)
        .join(Photo, Photo.id == PhotoTag.photo_id)
        .where(PhotoTag.photo_id == photo_id, PhotoTag.user_id == user_id)
    )
    result = await session.execute(stmt)
    return result.one_or_none()


async def set_tag_review_status(
    session: AsyncSession,
    tag: PhotoTag,
    *,
    status: Literal["confirmed", "rejected"],
    source: Literal["guest_confirmed"] | None = None,
) -> PhotoTag:
    tag.status = status
    if source is not None:
        tag.source = source
    await session.commit()
    return tag
