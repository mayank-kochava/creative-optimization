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
