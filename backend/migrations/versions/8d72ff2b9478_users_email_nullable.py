"""users email nullable

Revision ID: 8d72ff2b9478
Revises: 82dabc4137c8
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8d72ff2b9478'
down_revision: Union[str, Sequence[str], None] = '82dabc4137c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Supabase anonymous sign-in (guests joining via invite link) issues a
    # JWT with no email claim, so users.email must accept NULL. The UNIQUE
    # constraint still holds — Postgres treats each NULL as distinct.
    op.alter_column('users', 'email',
        existing_type=postgresql.CITEXT(),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'email',
        existing_type=postgresql.CITEXT(),
        nullable=False,
    )
