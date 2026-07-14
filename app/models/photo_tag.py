import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, REAL
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin


class PhotoTag(CreatedAtMixin, Base):
    __tablename__ = "photo_tags"
    __table_args__ = (
        CheckConstraint(
            "status IN ('confirmed', 'pending_guest', 'rejected')",
            name="ck_photo_tags_status",
        ),
        CheckConstraint(
            "source IN ('auto', 'guest_confirmed', 'host_action')",
            name="ck_photo_tags_source",
        ),
        # Powers the "Photos of You" query: a user's confirmed tags, one lookup.
        Index("idx_tags_user", "user_id", "status"),
    )

    # Composite primary key: at most one tag per (photo, user), no matter how
    # many detected faces matched them.
    photo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Which face matched; kept loosely so the tag can survive face deletion.
    face_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("faces.id", ondelete="SET NULL"))
    similarity: Mapped[float] = mapped_column(REAL)
    status: Mapped[str] = mapped_column(default="confirmed", server_default="confirmed")
    source: Mapped[str] = mapped_column(default="auto", server_default="auto")
