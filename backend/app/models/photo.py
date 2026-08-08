import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Photo(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "photos"
    __table_args__ = (
        CheckConstraint(
            "status IN ('awaiting_upload', 'queued', 'processing', 'processed', 'failed')",
            name="ck_photos_status",
        ),
        # Progress polling: count photos in an event grouped by status.
        Index("idx_photos_event_status", "event_id", "status"),
        # Gallery listing: newest-first within an event.
        Index("idx_photos_event_taken", "event_id", text("taken_at DESC")),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    # No ON DELETE CASCADE: an uploader's account is not expected to
    # disappear while their photos still exist.
    uploader_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    original_key: Mapped[str]
    # Set during processing.
    web_key: Mapped[str | None]
    thumb_key: Mapped[str | None]
    width: Mapped[int | None]
    height: Mapped[int | None]
    # From EXIF; used for gallery ordering.
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(default="awaiting_upload", server_default="awaiting_upload")
