from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean
from typing import List, TYPE_CHECKING
from .base import Base

if TYPE_CHECKING:
    from .user_preferences import UserPreferences

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    preferences: Mapped[List["UserPreferences"]] = relationship(
        "UserPreferences", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # Add relationship to scan history
    scan_history: Mapped[List["ScanHistory"]] = relationship(
        "ScanHistory", 
        back_populates="user",
        cascade="all, delete-orphan"
    )