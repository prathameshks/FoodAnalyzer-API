from sqlalchemy import Column, Integer, String, JSON
from .base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, nullable=False)
    generic_name = Column(String, nullable=True)
    brands = Column(String, nullable=True)
    ingredients = Column(JSON, nullable=True)
    ingredients_text = Column(String, nullable=True)
    ingredients_analysis = Column(JSON, nullable=True)
    nutriscore = Column(JSON, nullable=True)
    nutrient_levels = Column(JSON, nullable=True)
    nutriments = Column(JSON, nullable=True)
    data_quality_warnings = Column(JSON, nullable=True)
