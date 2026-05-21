"""Add search_tags to creative_analyses

Revision ID: 003
Revises: 002
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'creative_analyses',
        sa.Column('search_tags', postgresql.JSONB(), server_default='[]', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('creative_analyses', 'search_tags')
