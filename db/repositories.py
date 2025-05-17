from sqlalchemy.orm import Session
from sqlalchemy import cast, or_, String
from sqlalchemy.dialects.postgresql import JSONB

import json
from logger_manager import log_debug, log_error
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
            log_debug(f"Exact match found for ingredient: {name}")
            return exact_match
        
        # If no exact match, try searching in alternate names
        try:
            # Use .first() to return the model instance, not the query object
            alternate_match = self.db.query(models.Ingredient).filter(
                models.Ingredient.alternate_names.cast(JSONB).op('?')(name)
            ).first()
            
            if alternate_match:
                log_debug(f"Alternate match found for ingredient: {name}")
            
            return alternate_match
        except Exception as e:
            log_error(f"Error searching alternate names: {e}",e)
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


class OpenFoodFactsRepository:
    def __init__(self, db: Session):
        self.db = db

    # Keep the save_open_food_facts_data method if you still need to save product-level data
    # based on our previous discussion. If not, you can remove it.

    def save_open_food_facts_ingredient_data(self, open_food_facts_response: dict):
        """
        Extracts ingredient data from an Open Food Facts API response and saves or updates it
        in the open_food_facts_ingredients_data table.

        Args:
            open_food_facts_response: The JSON response from the Open Food Facts API.
        """
        if open_food_facts_response.get("status") == 1 and "product" in open_food_facts_response:
            product_data = open_food_facts_response["product"]
            ingredients_list = product_data.get("ingredients", [])

            for ingredient in ingredients_list:
                ingredient_text = ingredient.get("text")
                if not ingredient_text:
                    continue # Skip if ingredient text is missing

                # Check if ingredient data already exists
                existing_ingredient = self.db.query(models.OpenFoodFactsIngredientsData).filter(models.OpenFoodFactsIngredientsData.ingredient_text == ingredient_text).first()

                open_food_facts_id = ingredient.get("id")
                vegan = ingredient.get("vegan", -1) # Default to -1 if unknown
                vegetarian = ingredient.get("vegetarian", -1) # Default to -1 if unknown
                has_allergens = 1 if ingredient.get("allergens") else 0 # Flag if allergens key exists
                allergens_tags = ",".join(ingredient.get("allergens", [])) # Allergens for the specific ingredient

                if existing_ingredient:
                    # Update existing ingredient data
                    existing_ingredient.open_food_facts_id = open_food_facts_id
                    existing_ingredient.vegan = vegan
                    existing_ingredient.vegetarian = vegetarian
                    existing_ingredient.has_allergens = has_allergens
                    existing_ingredient.allergens_tags = allergens_tags
                    # Update other fields as needed
                else:
                    # Create new ingredient data entry
                    new_ingredient_data = models.OpenFoodFactsIngredientsData(
                        ingredient_text=ingredient_text,
                        open_food_facts_id=open_food_facts_id,
                        vegan=vegan,
                        vegetarian=vegetarian,
                        has_allergens=has_allergens,
                        allergens_tags=allergens_tags
                        # Add other fields
                    )
                    self.db.add(new_ingredient_data)

                try:
                    self.db.commit()
                    if not existing_ingredient:
                         self.db.refresh(new_ingredient_data)
                except IntegrityError:
                    self.db.rollback()
                    log_debug(f"Ingredient '{ingredient_text}' already exists, skipping insertion.")
                except Exception as e:
                    self.db.rollback()
                    log_error(f"Error saving Open Food Facts ingredient data for '{ingredient_text}': {e}")


    def get_open_food_facts_ingredient_data(self, ingredient_text: str):
        """
        Retrieves Open Food Facts ingredient data from the database by ingredient text.

        Args:
            ingredient_text: The text of the ingredient.

        Returns:
            An OpenFoodFactsIngredientsData object if found, otherwise None.
        """
        if not ingredient_text:
            return None
        return self.db.query(models.OpenFoodFactsIngredientsData).filter(models.OpenFoodFactsIngredientsData.ingredient_text == ingredient_text).first()

    def __init__(self, db: Session):
        self.db = db

    def save_open_food_facts_data(self, open_food_facts_response: dict):
        """
        Extracts data from an Open Food Facts API response and saves or updates it in the database.

        Args:
            open_food_facts_response: The JSON response from the Open Food Facts API.
        """
        if open_food_facts_response.get("status") == 1 and "product" in open_food_facts_response:
            product_data = open_food_facts_response["product"]

            code = open_food_facts_response.get("code")
            if not code:
                log_error("Open Food Facts response missing product code.")
                return

            # Check if a record with the same code already exists
            existing_product = self.db.query(models.OpenFoodFactsData).filter(models.OpenFoodFactsData.code == code).first()

            product_name = product_data.get("product_name")
            ingredients_text = product_data.get("ingredients_text")
            ingredients_json = json.dumps(product_data.get("ingredients")) if product_data.get("ingredients") is not None else None
            allergens_tags = ",".join(product_data.get("allergens_tags", []))
            traces_tags = ",".join(product_data.get("traces_tags", []))
            nova_group = product_data.get("nova_group")
            ecoscore_score = product_data.get("ecoscore_score")
            nutriments_json = json.dumps(product_data.get("nutriments")) if product_data.get("nutriments") is not None else None
            nutrition_grade_fr = product_data.get("nutrition_grade_fr")
            url = product_data.get("url")

            if existing_product:
                # Update the existing record
                existing_product.product_name = product_name
                existing_product.ingredients_text = ingredients_text
                existing_product.ingredients_json = ingredients_json
                existing_product.allergens_tags = allergens_tags
                existing_product.traces_tags = traces_tags
                existing_product.nova_group = nova_group
                existing_product.ecoscore_score = ecoscore_score
                existing_product.nutriments_json = nutriments_json
                existing_product.nutrition_grade_fr = nutrition_grade_fr
                existing_product.url = url
            else:
                # Create a new OpenFoodFactsData object
                new_product_data = models.OpenFoodFactsData(
                    code=code,
                    product_name=product_name,
                    ingredients_text=ingredients_text,
                    ingredients_json=ingredients_json,
                    allergens_tags=allergens_tags,
                    traces_tags=traces_tags,
                    nova_group=nova_group,
                    ecoscore_score=ecoscore_score,
                    nutriments_json=nutriments_json,
                    nutrition_grade_fr=nutrition_grade_fr,
                    url=url
                )
                self.db.add(new_product_data)

            try:
                self.db.commit()
                if not existing_product:
                     self.db.refresh(new_product_data) # Refresh only for new objects
            except Exception as e:
                self.db.rollback()
                log_error(f"Error saving Open Food Facts data: {e}")


    def get_open_food_facts_data_by_code(self, product_code: str):
        """
        Retrieves Open Food Facts data from the database by product code.

        Args:
            product_code: The barcode of the product.

        Returns:
            An OpenFoodFactsData object if found, otherwise None.
        """
        if not product_code:
            return None
        return self.db.query(models.OpenFoodFactsData).filter(models.OpenFoodFactsData.code == product_code).first()