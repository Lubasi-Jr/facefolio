import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Invitation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "invitations"
    __table_args__ = (
        CheckConstraint("role IN ('host', 'guest')", name="ck_invitations_role"),
        CheckConstraint(
            "status IN ('pending', 'joined', 'revoked')",
            name="ck_invitations_status",
        ),
        # A person can only be a member of a given event once.
        UniqueConstraint("event_id", "user_id", name="uq_invitations_event_user"),
        Index("idx_invitations_event", "event_id"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    # Encoded in the QR code / share link that a guest uses to join.
    invite_token: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str | None] = mapped_column(CITEXT)
    # NULL until the invite is claimed.
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(default="guest", server_default="guest")
    status: Mapped[str] = mapped_column(default="pending", server_default="pending")
