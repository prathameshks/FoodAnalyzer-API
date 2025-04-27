from sqlalchemy.orm import Session
from sqlalchemy import cast, or_, String
from sqlalchemy.dialects.postgresql import JSONB
from . import models
from interfaces.ingredientModels import IngredientAnalysisResult 
from interfaces.productModels import ProductCreate
from datetime import datetime
    
class IngredientRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_ingredient_by_name(self, name: str):        
        exact_match = self.db.query(models.Ingredient).filter(models.Ingredient.name.ilike(name)).first()
    
        if exact_match:
            return exact_match
        
        # If no exact match, try searching in alternate names
        try:
            # Use .first() to return the model instance, not the query object
            alternate_match = self.db.query(models.Ingredient).filter(
                models.Ingredient.alternate_names.cast(JSONB).op('?')(name)
            ).first()
            
            return alternate_match
        except Exception as e:
            from logger_manager import logger
            logger.error(f"Error searching alternate names: {e}")
            return None
        
    def get_all_ingredients(self, skip: int = 0, limit: int = 100):
        return self.db.query(models.Ingredient).offset(skip).limit(limit).all()
    
    def create_ingredient(self, ingredient_data: IngredientAnalysisResult):
        # Create ingredient record
        db_ingredient = models.Ingredient(
            name=ingredient_data.name,
            alternate_names=ingredient_data.alternate_names,
            safety_rating=ingredient_data.safety_rating,
            description=ingredient_data.description,
            health_effects=ingredient_data.health_effects,
            allergic_info=ingredient_data.allergic_info,
            diet_type=ingredient_data.diet_type
        )
        self.db.add(db_ingredient)
        self.db.commit()
        self.db.refresh(db_ingredient)
        
        # Create source records
        for source in ingredient_data.details_with_source:
            db_source = models.IngredientSource(
                ingredient_id=db_ingredient.id,
                source_name=source.get("source", "Unknown"),
                found=source.get("found", False),
                summary=source.get("summary", ""),
                data=source
            )
            self.db.add(db_source)
        
        self.db.commit()
        return db_ingredient
    
    def update_ingredient(self, name: str, ingredient_data: IngredientAnalysisResult):
        db_ingredient = self.get_ingredient_by_name(name)
        if db_ingredient:
            # Update ingredient fields
            db_ingredient.alternate_names = ingredient_data.alternate_names
            db_ingredient.safety_rating = ingredient_data.safety_rating
            db_ingredient.description = ingredient_data.description
            db_ingredient.health_effects = ingredient_data.health_effects
            
            # Delete old sources
            self.db.query(models.IngredientSource).filter(
                models.IngredientSource.ingredient_id == db_ingredient.id
            ).delete()
            
            # Create new sources
            for source in ingredient_data.details_with_source:
                db_source = models.IngredientSource(
                    ingredient_id=db_ingredient.id,
                    source_name=source.get("source", "Unknown"),
                    found=source.get("found", False),
                    summary=source.get("summary", ""),
                    data=source
                )
                self.db.add(db_source)
            
            self.db.commit()
            self.db.refresh(db_ingredient)
            return db_ingredient
        return None

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def add_product(self, product_create: ProductCreate):
        db_product = self._create_product(product_create)
        self._store_analysis_data(db_product, product_create.ingredients_analysis)
        return db_product

    def _create_product(self, product_create: ProductCreate):
        db_product = models.Product(
            product_name=product_create.product_name,
            ingredients=product_create.ingredients,
            overall_safety_score=product_create.overall_safety_score,
            suitable_diet_types=product_create.suitable_diet_types,
            allergy_warnings=product_create.allergy_warnings,
            usage_recommendations=product_create.usage_recommendations,
            health_insights=product_create.health_insights,
            ingredient_interactions=product_create.ingredient_interactions,
            key_takeaway=product_create.key_takeaway,
            ingredients_count=product_create.ingredients_count,
            user_id=product_create.user_id,
            timestamp=product_create.timestamp,
            ingredient_ids=product_create.ingredient_ids
        )
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return db_product

    def _store_analysis_data(self, db_product, ingredients_analysis):
        db_product.ingredients_analysis = ingredients_analysis
        self.db.commit()
        self.db.refresh(db_product)
