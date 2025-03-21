from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    dietary_restrictions = Column(String, nullable=True)
    allergens = Column(String, nullable=True)
    preferred_ingredients = Column(String, nullable=True)
    disliked_ingredients = Column(String, nullable=True)

    user = relationship("User", back_populates="preferences")
