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
    assert any("creative_id" in str(c) for c in CreativeMetric.__table__.constraints)
