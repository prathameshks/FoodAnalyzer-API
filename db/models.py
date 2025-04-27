from sqlalchemy import Column, Integer, String, Boolean, Text, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from .database import Base
from typing import List, Optional
from datetime import datetime


class Ingredient(Base):
    __tablename__ = "ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    alternate_names = Column(JSON, nullable=True)
    safety_rating = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    health_effects = Column(JSON, nullable=True)
    allergic_info = Column(JSON, nullable=True)
    diet_type = Column(String, nullable=True)  
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    sources = relationship("IngredientSource", back_populates="ingredient")
    
class IngredientSource(Base):
    __tablename__ = "ingredient_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    source_name = Column(String, nullable=False)
    found = Column(Boolean, default=False)
    summary = Column(Text, nullable=True)
    data = Column(JSON, nullable=True)
    
    # Relationships
    ingredient = relationship("Ingredient", back_populates="sources")
    
class Marker(Base):
    __tablename__ = "markers"
    id: Mapped[int] = mapped_column(primary_key=True)
    image_name: Mapped[str]
    vuforia_id: Mapped[str]
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))

    product: Mapped["Product"] = relationship(back_populates="markers")

class Product(Base):
    
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, nullable=False)
    ingredients = Column(JSON, nullable=True)
    ingredients_analysis = Column(JSON, nullable=True)
    overall_safety_score = Column(Integer, nullable=True)
    suitable_diet_types = Column(String, nullable=True)
    allergy_warnings = Column(JSON, nullable=True)
    usage_recommendations = Column(String, nullable=True)
    health_insights = Column(JSON, nullable=True)
    ingredient_interactions = Column(JSON, nullable=True)
    key_takeaway = Column(String, nullable=True)
    ingredients_count = Column(Integer, nullable=True)
    user_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    ingredient_ids= Column(JSON, nullable=True)
    
    data_quality_warnings = Column(JSON, nullable=True)
    markers: Mapped[List["Marker"]] = relationship(back_populates="product")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=False, index=False, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    preferences = relationship(
        "UserPreferences", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    scan_history = relationship(
        "ScanHistory", 
        back_populates="user",
        cascade="all, delete-orphan"
    )

class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    dietary_restrictions = Column(String, nullable=True)
    allergens = Column(String, nullable=True)
    preferred_ingredients = Column(String, nullable=True)
    disliked_ingredients = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="preferences")

class ScanHistory(Base):
    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    product_id = Column(Integer)
    scan_date = Column(DateTime, default=datetime.now)

    # Relationships
    user = relationship("User", back_populates="scan_history")
