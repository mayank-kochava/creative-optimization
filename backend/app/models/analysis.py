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
    search_tags: Mapped[list] = mapped_column(JSONB, server_default="[]")
    analysed_at: Mapped[datetime] = mapped_column(server_default=func.now())

    creative: Mapped["Creative"] = relationship("Creative", back_populates="analysis")
