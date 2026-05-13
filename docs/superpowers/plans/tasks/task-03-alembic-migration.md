# Task 03: Alembic Migration

**Files to create:**
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/001_initial_schema.py`

**Prereq:** Task 02 complete (all models exist).

---

## Step 1: Write failing test

```python
# backend/tests/test_migration.py
import pytest
import asyncpg


@pytest.mark.asyncio
async def test_migration_creates_all_tables():
    """Run alembic upgrade head and verify all tables exist."""
    import subprocess
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd="backend",
        capture_output=True, text=True,
        env={**os.environ, "DATABASE_URL": "postgresql+asyncpg://appuser:apppassword@localhost:5432/creative_opt_test"}
    )
    assert result.returncode == 0, result.stderr

    conn = await asyncpg.connect("postgresql://appuser:apppassword@localhost:5432/creative_opt_test")
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public'"
    )
    table_names = {r['tablename'] for r in tables}
    await conn.close()

    assert "campaigns" in table_names
    assert "creatives" in table_names
    assert "creative_analyses" in table_names
    assert "creative_annotations" in table_names
    assert "creative_metrics" in table_names
    assert "duplicate_pairs" in table_names
```

Run: `cd backend && pytest tests/test_migration.py -v`
Expected: FAIL — `alembic.ini` not found.

---

## Step 2: Create `backend/alembic.ini`

```ini
[alembic]
script_location = alembic
file_template = %%(rev)s_%%(slug)s
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://appuser:apppassword@localhost:5432/creative_opt

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

---

## Step 3: Create `backend/alembic/env.py`

```python
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.database import Base
import app.models  # noqa: F401 — ensure all models are imported for autogenerate

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

DATABASE_URL = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url"))


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## Step 4: Create `backend/alembic/script.py.mako`

```
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

---

## Step 5: Create `backend/alembic/versions/001_initial_schema.py`

```python
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
        sa.UniqueConstraint('phash', name='uq_creatives_phash'),
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
```

---

## Step 6: Run migration

```bash
cd backend
docker-compose up -d postgres  # must be running
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema
```

---

## Step 7: Run tests

```bash
pytest tests/test_migration.py -v
```

Expected: PASS.

---

## Step 8: Commit

```bash
git add backend/alembic* backend/alembic.ini
git commit -m "feat: Alembic initial migration — 6 tables with indexes and constraints"
```
