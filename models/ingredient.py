from sqlalchemy import Column, Integer, String, JSON, Boolean
from .base import Base

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    nutritional_info = Column(JSON)
    description = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    allergens = Column(String, nullable=True)
    vegan = Column(Boolean, nullable=True)
    vegetarian = Column(Boolean, nullable=True)
