from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Integer, DateTime
from datetime import datetime
from .base import Base
from typing import Optional

class ScanHistory(Base):
    __tablename__ = "scan_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(Integer)
    scan_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Add relationship to user
    user: Mapped["User"] = relationship("User", back_populates="scan_history")