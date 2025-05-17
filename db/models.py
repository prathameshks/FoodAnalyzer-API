from sqlalchemy import Column, Integer, String, Boolean, Text, JSON, ForeignKey, DateTime, text,TIMESTAMP
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from .database import Base
from typing import List, Optional
from datetime import datetime


class Ingredient(Base):
    __tablename__ = "ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)
    alternate_names = Column(Text, nullable=True)
    safety_rating = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    health_effects = Column(Text, nullable=True)
    allergic_info = Column(Text, nullable=True)
    diet_type = Column(String(255), nullable=True)  
    # Fix the default timestamp for MySQL
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime(timezone=True),nullable=True)
    
    # Relationships
    sources = relationship("IngredientSource", back_populates="ingredient")
    
class IngredientSource(Base):
    __tablename__ = "ingredient_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    source_name = Column(String(255), nullable=False)
    found = Column(Boolean, default=False)
    summary = Column(Text, nullable=True)
    data = Column(Text, nullable=True)
    
    # Relationships
    ingredient = relationship("Ingredient", back_populates="sources")
    
class Marker(Base):
    __tablename__ = "markers"
    
    id = Column(Integer, primary_key=True, index=True)
    image_name = Column(String(255), nullable=False)
    vuforia_id = Column(String(255), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))

    # Traditional relationship syntax
    product = relationship("Product", back_populates="markers")
    
class Product(Base):
    
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(255), nullable=False)
    ingredients = Column(Text, nullable=True)
    ingredients_analysis = Column(Text, nullable=True)
    overall_safety_score = Column(Integer, nullable=True)
    suitable_diet_types = Column(String(255), nullable=True)
    allergy_warnings = Column(Text, nullable=True)
    usage_recommendations = Column(Text, nullable=True)
    health_insights = Column(Text, nullable=True)
    ingredient_interactions = Column(Text, nullable=True)
    key_takeaway = Column(Text, nullable=True)
    ingredients_count = Column(Integer, nullable=True)
    user_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    ingredient_ids= Column(Text, nullable=True)
    
    data_quality_warnings = Column(Text, nullable=True)
    markers: Mapped[List["Marker"]] = relationship(back_populates="product")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=False, index=False, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)  
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
    dietary_restrictions = Column(String(255), nullable=True)
    allergens = Column(Text, nullable=True)
    preferred_ingredients = Column(Text, nullable=True)
    disliked_ingredients = Column(Text, nullable=True)

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


class OpenFoodFactsIngredientsData(Base):
    __tablename__ = 'open_food_facts_ingredients_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ingredient_text = Column(Text, unique=True)
    open_food_facts_id = Column(String(255))
    vegan = Column(Integer)
    vegetarian = Column(Integer)
    has_allergens = Column(Integer)
    allergens_tags = Column(Text)
    # Add other fields as per schema
