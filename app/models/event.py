import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Event(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'expired', 'purged')",
            name="ck_events_status",
        ),
        # Partial index: the purge job only scans still-active events past
        # their expiry, so only those rows need to be indexed.
        Index("idx_events_expiry", "expires_at", postgresql_where=text("status = 'active'")),
    )

    # No ON DELETE CASCADE: a host's account is not expected to disappear
    # while their events still exist.
    host_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    event_date: Mapped[date | None]
    # Drives the scheduled biometric purge job.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(default="active", server_default="active")
