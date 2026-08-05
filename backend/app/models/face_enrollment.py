import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, REAL, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class FaceEnrollment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "face_enrollments"
    __table_args__ = (
        # One baseline selfie per guest per event.
        UniqueConstraint("event_id", "user_id", name="uq_face_enrollments_event_user"),
        # Scopes match queries to a single event's enrollments.
        Index("idx_enrollments_event", "event_id"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    selfie_key: Mapped[str]
    # L2-normalized face vector.
    embedding: Mapped[list[float]] = mapped_column(Vector(512))
    quality_score: Mapped[float] = mapped_column(REAL)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
