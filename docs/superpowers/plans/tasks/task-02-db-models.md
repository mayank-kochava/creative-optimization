# Task 02: Database Models

**Files to create:**
- `backend/app/models/campaign.py`
- `backend/app/models/creative.py`
- `backend/app/models/analysis.py`
- `backend/app/models/annotation.py`
- `backend/app/models/metric.py`
- `backend/app/models/duplicate.py`
- `backend/app/models/__init__.py`

**Prereq:** Task 01 complete (`backend/app/database.py` exists with `Base`).

---

## Step 1: Write failing test

```python
# backend/tests/test_models.py
import pytest
from sqlalchemy import inspect
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.analysis import CreativeAnalysis
from app.models.annotation import CreativeAnnotation
from app.models.metric import CreativeMetric
from app.models.duplicate import DuplicatePair


def test_campaign_table_name():
    assert Campaign.__tablename__ == "campaigns"


def test_creative_has_phash_column():
    cols = {c.name for c in Creative.__table__.columns}
    assert "phash" in cols
    assert "fatigue_status" in cols


def test_analysis_has_scores_column():
    cols = {c.name for c in CreativeAnalysis.__table__.columns}
    assert "scores" in cols
    assert "overall_score" in cols
    assert "benchmark_percentile" in cols


def test_metric_unique_constraint():
    constraints = {c.name for c in CreativeMetric.__table__.constraints}
    # unique constraint on (creative_id, date) should exist
    assert any("creative_id" in str(c) for c in CreativeMetric.__table__.constraints)
```

Run: `cd backend && pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError`

---

## Step 2: Create `backend/app/models/campaign.py`

```python
from datetime import datetime
from typing import Optional

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform_tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), server_default="{}")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    creatives: Mapped[list["Creative"]] = relationship("Creative", back_populates="campaign")
```

---

## Step 3: Create `backend/app/models/creative.py`

```python
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Creative(Base):
    __tablename__ = "creatives"
    __table_args__ = (
        Index("idx_creatives_campaign_id", "campaign_id"),
        Index("idx_creatives_phash", "phash"),
        Index("idx_creatives_fatigue_status", "fatigue_status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("campaigns.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    phash: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    fatigue_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="insufficient_data")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="creatives")
    analysis: Mapped[Optional["CreativeAnalysis"]] = relationship("CreativeAnalysis", back_populates="creative", uselist=False)
    annotations: Mapped[list["CreativeAnnotation"]] = relationship("CreativeAnnotation", back_populates="creative")
    metrics: Mapped[list["CreativeMetric"]] = relationship("CreativeMetric", back_populates="creative")
```

---

## Step 4: Create `backend/app/models/analysis.py`

```python
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CreativeAnalysis(Base):
    __tablename__ = "creative_analyses"
    __table_args__ = (
        Index("idx_analyses_overall_score", "overall_score"),
        Index("idx_analyses_benchmark_percentile", "benchmark_percentile"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    creative_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("creatives.id", ondelete="CASCADE"), unique=True)
    scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    persuasion_strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    dominant_emotion: Mapped[str] = mapped_column(String(50), nullable=False)
    strengths: Mapped[list] = mapped_column(JSONB, server_default="[]")
    weaknesses: Mapped[list] = mapped_column(JSONB, server_default="[]")
    recommendations: Mapped[list] = mapped_column(JSONB, server_default="[]")
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    benchmark_percentile: Mapped[Optional[int]] = mapped_column(Integer)
    benchmark_corpus_size: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="complete")
    analysed_at: Mapped[datetime] = mapped_column(server_default=func.now())

    creative: Mapped["Creative"] = relationship("Creative", back_populates="analysis")
```

---

## Step 5: Create `backend/app/models/annotation.py`

```python
from typing import Optional

from sqlalchemy import BigInteger, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CreativeAnnotation(Base):
    __tablename__ = "creative_annotations"
    __table_args__ = (Index("idx_annotations_creative_id", "creative_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    creative_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("creatives.id", ondelete="CASCADE"))
    annotation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    bbox: Mapped[dict] = mapped_column(JSONB, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255))
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    creative: Mapped["Creative"] = relationship("Creative", back_populates="annotations")
```

---

## Step 6: Create `backend/app/models/metric.py`

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CreativeMetric(Base):
    __tablename__ = "creative_metrics"
    __table_args__ = (
        UniqueConstraint("creative_id", "date", name="uq_metric_creative_date"),
        Index("idx_metrics_creative_date", "creative_id", "date"),
        Index("idx_metrics_date", "date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    creative_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("creatives.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    installs: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    spend: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, server_default="0")
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, server_default="0")

    creative: Mapped["Creative"] = relationship("Creative", back_populates="metrics")
```

---

## Step 7: Create `backend/app/models/duplicate.py`

```python
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DuplicatePair(Base):
    __tablename__ = "duplicate_pairs"
    __table_args__ = (
        UniqueConstraint("creative_id_a", "creative_id_b", name="uq_duplicate_pair"),
        Index("idx_duplicates_creative_a", "creative_id_a"),
        Index("idx_duplicates_creative_b", "creative_id_b"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    creative_id_a: Mapped[int] = mapped_column(BigInteger, ForeignKey("creatives.id", ondelete="CASCADE"))
    creative_id_b: Mapped[int] = mapped_column(BigInteger, ForeignKey("creatives.id", ondelete="CASCADE"))
    hamming_distance: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_type: Mapped[str] = mapped_column(String(20), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

---

## Step 8: Update `backend/app/models/__init__.py`

```python
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.analysis import CreativeAnalysis
from app.models.annotation import CreativeAnnotation
from app.models.metric import CreativeMetric
from app.models.duplicate import DuplicatePair

__all__ = ["Campaign", "Creative", "CreativeAnalysis", "CreativeAnnotation", "CreativeMetric", "DuplicatePair"]
```

---

## Step 9: Run tests

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: all 4 tests PASS.

---

## Step 10: Commit

```bash
git add backend/app/models/
git commit -m "feat: SQLAlchemy 2.0 ORM models — all 6 entities"
```
