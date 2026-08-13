from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "users"

    # citext makes email comparisons case-insensitive at the DB level, so
    # "A@x.com" and "a@x.com" collide on the UNIQUE constraint.
    # Nullable: Supabase anonymous sign-in (guests joining via invite link)
    # issues a JWT with no email claim.
    email: Mapped[str | None] = mapped_column(CITEXT, unique=True)
    display_name: Mapped[str]
