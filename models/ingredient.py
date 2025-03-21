from sqlalchemy import Column, Integer, String, JSON
from database import Base

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    nutritional_info = Column(JSON)
