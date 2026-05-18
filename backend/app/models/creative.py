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
    phash: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fatigue_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="insufficient_data")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="creatives")
    analysis: Mapped[Optional["CreativeAnalysis"]] = relationship("CreativeAnalysis", back_populates="creative", uselist=False)
    annotations: Mapped[list["CreativeAnnotation"]] = relationship("CreativeAnnotation", back_populates="creative")
    metrics: Mapped[list["CreativeMetric"]] = relationship("CreativeMetric", back_populates="creative")
