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
