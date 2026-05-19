"""Drop unique constraint on creatives.phash

Revision ID: 002
Revises: 001
Create Date: 2026-05-19
"""
from alembic import op

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('uq_creatives_phash', 'creatives', type_='unique')


def downgrade() -> None:
    op.create_unique_constraint('uq_creatives_phash', 'creatives', ['phash'])
