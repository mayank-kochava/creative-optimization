"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'campaigns',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('platform_tags', postgresql.ARRAY(sa.String()), server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_campaigns_created_at', 'campaigns', [sa.text('created_at DESC')])

    op.create_table(
        'creatives',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('campaign_id', sa.BigInteger(), nullable=False),
        sa.Column('filename', sa.String(512), nullable=False),
        sa.Column('storage_path', sa.String(1024), nullable=False),
        sa.Column('format', sa.String(10), nullable=False),
        sa.Column('width', sa.Integer()),
        sa.Column('height', sa.Integer()),
        sa.Column('duration_seconds', sa.Float()),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('phash', sa.BigInteger(), nullable=False),
        sa.Column('fatigue_status', sa.String(20), nullable=False, server_default='insufficient_data'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
sa.CheckConstraint("format IN ('jpg','png','webp','gif','mp4','mov')", name='ck_creative_format'),
        sa.CheckConstraint("fatigue_status IN ('healthy','fatiguing','insufficient_data')", name='ck_fatigue_status'),
    )
    op.create_index('idx_creatives_campaign_id', 'creatives', ['campaign_id'])
    op.create_index('idx_creatives_phash', 'creatives', ['phash'])
    op.create_index('idx_creatives_fatigue_status', 'creatives', ['fatigue_status'])

    op.create_table(
        'creative_analyses',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('creative_id', sa.BigInteger(), nullable=False),
        sa.Column('scores', postgresql.JSONB(), nullable=False),
        sa.Column('overall_score', sa.Integer(), nullable=False),
        sa.Column('persuasion_strategy', sa.String(50), nullable=False),
        sa.Column('dominant_emotion', sa.String(50), nullable=False),
        sa.Column('strengths', postgresql.JSONB(), server_default='[]'),
        sa.Column('weaknesses', postgresql.JSONB(), server_default='[]'),
        sa.Column('recommendations', postgresql.JSONB(), server_default='[]'),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('benchmark_percentile', sa.Integer()),
        sa.Column('benchmark_corpus_size', sa.Integer()),
        sa.Column('status', sa.String(20), nullable=False, server_default='complete'),
        sa.Column('analysed_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('overall_score BETWEEN 0 AND 10', name='ck_overall_score'),
        sa.CheckConstraint('benchmark_percentile BETWEEN 1 AND 100', name='ck_benchmark_pct'),
        sa.CheckConstraint("status IN ('complete','degraded')", name='ck_analysis_status'),
        sa.ForeignKeyConstraint(['creative_id'], ['creatives.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('creative_id', name='uq_analysis_creative_id'),
    )
    op.create_index('idx_analyses_overall_score', 'creative_analyses', [sa.text('overall_score DESC')])

    op.create_table(
        'creative_annotations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('creative_id', sa.BigInteger(), nullable=False),
        sa.Column('annotation_type', sa.String(20), nullable=False),
        sa.Column('bbox', postgresql.JSONB(), nullable=False),
        sa.Column('label', sa.String(255)),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.CheckConstraint("annotation_type IN ('face','text','cta')", name='ck_annotation_type'),
        sa.CheckConstraint('confidence BETWEEN 0 AND 1', name='ck_annotation_confidence'),
        sa.ForeignKeyConstraint(['creative_id'], ['creatives.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_annotations_creative_id', 'creative_annotations', ['creative_id'])

    op.create_table(
        'creative_metrics',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('creative_id', sa.BigInteger(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('impressions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('clicks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('installs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('spend', sa.Numeric(12, 4), nullable=False, server_default='0'),
        sa.Column('revenue', sa.Numeric(12, 4), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['creative_id'], ['creatives.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('creative_id', 'date', name='uq_metric_creative_date'),
    )
    op.create_index('idx_metrics_creative_date', 'creative_metrics', ['creative_id', sa.text('date DESC')])
    op.create_index('idx_metrics_date', 'creative_metrics', [sa.text('date DESC')])

    op.create_table(
        'duplicate_pairs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('creative_id_a', sa.BigInteger(), nullable=False),
        sa.Column('creative_id_b', sa.BigInteger(), nullable=False),
        sa.Column('hamming_distance', sa.Integer(), nullable=False),
        sa.Column('duplicate_type', sa.String(20), nullable=False),
        sa.Column('detected_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('hamming_distance BETWEEN 0 AND 10', name='ck_hamming_distance'),
        sa.CheckConstraint("duplicate_type IN ('self','cross_platform')", name='ck_duplicate_type'),
        sa.ForeignKeyConstraint(['creative_id_a'], ['creatives.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['creative_id_b'], ['creatives.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('creative_id_a', 'creative_id_b', name='uq_duplicate_pair'),
    )
    op.create_index('idx_duplicates_creative_a', 'duplicate_pairs', ['creative_id_a'])
    op.create_index('idx_duplicates_creative_b', 'duplicate_pairs', ['creative_id_b'])


def downgrade() -> None:
    op.drop_table('duplicate_pairs')
    op.drop_table('creative_metrics')
    op.drop_table('creative_annotations')
    op.drop_table('creative_analyses')
    op.drop_table('creatives')
    op.drop_table('campaigns')
