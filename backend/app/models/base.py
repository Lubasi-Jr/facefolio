import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    # Plain Mapped[str] renders as TEXT, matching docs/schema_facefolio.sql
    # (Postgres TEXT and VARCHAR are equivalent; this just keeps them literal).
    type_annotation_map = {str: Text}


class UUIDPrimaryKeyMixin:
    # gen_random_uuid() is Postgres-native and needs no round trip to Python,
    # unlike Python-side uuid4() defaults.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
