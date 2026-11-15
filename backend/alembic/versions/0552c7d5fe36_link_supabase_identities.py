"""link supabase identities

Revision ID: 0552c7d5fe36
Revises: d82b966f6b46
Create Date: 2026-11-13 17:37:14.422644
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0552c7d5fe36'
down_revision: Union[str, Sequence[str], None] = 'd82b966f6b46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('supabase_subject', sa.Uuid(), nullable=True))
    op.create_index('ix_users_supabase_subject', 'users', ['supabase_subject'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_supabase_subject', table_name='users')
    op.drop_column('users', 'supabase_subject')
