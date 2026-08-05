from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "users"

    # citext makes email comparisons case-insensitive at the DB level, so
    # "A@x.com" and "a@x.com" collide on the UNIQUE constraint.
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    display_name: Mapped[str]
