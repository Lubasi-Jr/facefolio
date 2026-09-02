"""add deletion log table

Revision ID: 8b4070ba18cd
Revises: 8d72ff2b9478
Create Date: 2026-09-02 20:53:42.053170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b4070ba18cd'
down_revision: Union[str, Sequence[str], None] = '8d72ff2b9478'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # No FK on event_id: this is the audit trail that a purge happened, and
    # must outlive the event row (and its cascade-deleted children) it refers
    # to. It records categories destroyed, never any biometric content.
    op.create_table('deletion_log',
    sa.Column('event_id', sa.UUID(), nullable=False),
    sa.Column('categories', sa.ARRAY(sa.Text()), nullable=False),
    sa.Column('db_purged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('storage_purged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_deletion_log_event', 'deletion_log', ['event_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_deletion_log_event', table_name='deletion_log')
    op.drop_table('deletion_log')
