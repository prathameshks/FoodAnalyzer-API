from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String
from typing import Optional, TYPE_CHECKING
from .base import Base

if TYPE_CHECKING:
    from .user import User

class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    dietary_restrictions: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    allergens: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    preferred_ingredients: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    disliked_ingredients: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="preferences")