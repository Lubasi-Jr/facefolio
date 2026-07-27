import uuid
from dataclasses import dataclass

import numpy as np
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face import Face


@dataclass
class FaceInsert:
    bbox: list[int]  # [x, y, w, h]
    det_score: float
    embedding: np.ndarray  # (512,) float32, L2-normalized


async def delete_faces_for_photo(session: AsyncSession, photo_id: uuid.UUID) -> None:
    # No commit here: this is the "delete" half of the delete-then-insert
    # idempotency pattern. It's meant to be followed by insert_faces() in the
    # same session, so both land in one transaction — if the task crashes
    # between the two, retrying re-runs the delete rather than leaving stale
    # rows next to a partial insert.
    await session.execute(delete(Face).where(Face.photo_id == photo_id))
    await session.flush()


async def insert_faces(
    session: AsyncSession,
    photo_id: uuid.UUID,
    event_id: uuid.UUID,
    faces: list[FaceInsert],
) -> list[Face]:
    rows = [
        Face(
            photo_id=photo_id,
            event_id=event_id,
            bbox=face.bbox,
            det_score=face.det_score,
            embedding=face.embedding.tolist(),
        )
        for face in faces
    ]
    session.add_all(rows)
    await session.commit()
    return rows
