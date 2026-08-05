import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, ForeignKey, Index, Integer, REAL
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class Face(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "faces"
    __table_args__ = (
        Index("idx_faces_photo", "photo_id"),
        # Enrollment-time matching and the purge job both filter faces by event.
        Index("idx_faces_event", "event_id"),
    )

    photo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("photos.id", ondelete="CASCADE"))
    # Denormalized from photos, so event-scoped queries never need that join.
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    # [x, y, w, h] face location; not biometric, survives the purge.
    bbox: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    det_score: Mapped[float] = mapped_column(REAL)
    # NULLABLE: set to NULL by the purge job on event expiry.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(512))
    # NULLABLE: cleared by the purge job on event expiry.
    crop_key: Mapped[str | None]
