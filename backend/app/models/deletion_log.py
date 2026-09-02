import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class DeletionLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Audit trail proving a biometric purge happened for an event — never
    the biometric content itself."""

    __tablename__ = "deletion_log"

    # No FK: this row must outlive the event row (and its cascade-deleted
    # children), which the purge it records may have already removed.
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    categories: Mapped[list[str]] = mapped_column(ARRAY(Text))
    db_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    storage_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
