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
