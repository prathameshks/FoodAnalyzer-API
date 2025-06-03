from sqlalchemy.orm import Session
from db.models import Marker, Product, Ingredient
from utils.analysis_utils import format_product_analysis_response
from logger_manager import log_info, log_error, log_debug
from interfaces.productModels import ProductAnalysisResponse
from typing import Optional, List
import json

def get_product_ingredients(db: Session, product: Product) -> List[dict]:
    """
    Fetch ingredients associated with a product.
    
    Args:
        db: Database session
        product: Product model instance
        
    Returns:
        List of ingredient data dictionaries
    """
    ingredient_data = []
    
    try:
        # Check if product has ingredient_ids field
        ingredient_ids = []
        
        if hasattr(product, 'ingredient_ids') and product.ingredient_ids:
            # Handle string or list format
            if isinstance(product.ingredient_ids, str):
                try:
                    ingredient_ids = [int(id.strip()) for id in product.ingredient_ids.split(',') if id.strip()]
                except:
                    try:
                        ingredient_ids = json.loads(product.ingredient_ids)
                    except:
                        log_error(f"Failed to parse ingredient_ids: {product.ingredient_ids}")
            elif isinstance(product.ingredient_ids, list):
                ingredient_ids = product.ingredient_ids
            
            log_info(f"Found {len(ingredient_ids)} ingredient IDs for product {product.id}")
            
            # Fetch ingredients by IDs
            for ing_id in ingredient_ids:
                ingredient = db.query(Ingredient).filter(Ingredient.id == ing_id).first()
                if ingredient:
                    ingredient_data.append({
                        "id": ingredient.id,
                        "name": ingredient.name,
                        "safety_rating": getattr(ingredient, "safety_rating", 5),
                        "description": getattr(ingredient, "description", ""),
                        "health_effects": getattr(ingredient, "health_effects", []),
                        "allergens": getattr(ingredient, "allergens", [])
                    })
        
        # If we still don't have ingredients, try looking for a relationship
        if not ingredient_data and hasattr(product, 'ingredients') and product.ingredients:
            for ingredient in product.ingredients:
                ingredient_data.append({
                    "id": ingredient.id,
                    "name": ingredient.name,
                    "safety_rating": getattr(ingredient, "safety_rating", 5),
                    "description": getattr(ingredient, "description", ""),
                    "health_effects": getattr(ingredient, "health_effects", []),
                    "allergens": getattr(ingredient, "allergens", [])
                })
                
        return ingredient_data
    except Exception as e:
        log_error(f"Error fetching ingredients for product {product.id}: {str(e)}")
        return []

def get_product_data_by_marker_id(db: Session, target_id: str) -> Optional[ProductAnalysisResponse]:
    """
    Retrieves product analysis and ingredient information by marker ID.

    Args:
        db: The database session.
        target_id: The target ID from the marker table.

    Returns:
        A ProductAnalysisResponse object or None if no product is found.
    """
    log_info(f"Attempting to retrieve product data for marker ID: {target_id}")
    try:
        # Find the marker with the given target_id
        marker = db.query(Marker).filter(Marker.vuforia_id == target_id).first()

        if not marker:
            log_info(f"No marker found for target ID: {target_id}")
            return None

        # Get the product associated with the marker
        product = db.query(Product).filter(Product.id == marker.product_id).first()

        if not product:
            log_info(f"No product found for product_id: {marker.product_id} linked to marker ID: {target_id}")
            return None

        log_info(f"Product found for marker ID {target_id}: {product.product_name}")
        
        # Log product fields for debugging
        log_info(f"Product fields: ID={product.id}, Name={product.product_name}")
        
        # Get ingredient details if needed
        ingredients = get_product_ingredients(db, product)
        if ingredients:
            log_info(f"Found {len(ingredients)} ingredients for product {product.id}")
            # Update product with ingredients if needed
            if not hasattr(product, 'ingredients_list') or not product.ingredients_list:
                product.ingredients_list = [ing["name"] for ing in ingredients]
            
            # Add ingredient analysis data if needed
            if not hasattr(product, 'ingredients_analysis') or not product.ingredients_analysis:
                product.ingredients_analysis = ingredients
        
        # Format the response using the utility function
        response_data = format_product_analysis_response(product)
        
        return response_data

    except Exception as e:
        log_error(f"Error retrieving product data for marker ID {target_id}: {str(e)}", e)
        return None