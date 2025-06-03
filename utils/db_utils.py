from typing import Dict, List,Any
from sqlalchemy.orm import Session
from interfaces.ingredientModels import IngredientAnalysisResult
from interfaces.productModels import ProductCreate
from db.models import Marker
from logger_manager import log_info, log_error
from fastapi import HTTPException
import os
from services.product_service import ProductService
from utils.vuforia_utils import add_target_to_vuforia
from env import UPLOADED_IMAGES_DIR # Assuming add_target_to_vuforia and UPLOADED_IMAGES_DIR are needed and will remain in product.py for now. If they are also moved, the import needs adjustment.
import json


def ingredient_db_to_pydantic(db_ingredient):
    """Convert a database ingredient model to a Pydantic model."""
    try:
        # Parse string fields that should be lists or dictionaries
        if isinstance(db_ingredient.alternate_names, str):
            alternate_names = json.loads(db_ingredient.alternate_names)
        else:
            alternate_names = db_ingredient.alternate_names or []
            
        if isinstance(db_ingredient.health_effects, str):
            health_effects = json.loads(db_ingredient.health_effects)
        else:
            health_effects = db_ingredient.health_effects or ["Unknown"]
            
        # Handle details_with_source, which should be a list of dictionaries
        if hasattr(db_ingredient, 'sources') and db_ingredient.sources:
            details = []
            for source in db_ingredient.sources:
                if isinstance(source.data, str):
                    try:
                        details.append(json.loads(source.data))
                    except json.JSONDecodeError:
                        details.append({"source": "Unknown", "data": source.data})
                else:
                    details.append(source.data)
        else:
            details = []
            
        return IngredientAnalysisResult(
            name=db_ingredient.name,
            alternate_names=alternate_names,
            is_found=True,
            id=db_ingredient.id,
            safety_rating=db_ingredient.safety_rating or 5,
            description=db_ingredient.description or "No description available",
            health_effects=health_effects,
            details_with_source=details
        )
    except Exception as e:
        log_error(f"Error converting DB ingredient to Pydantic model: {e}", e)
        # Fallback with minimal valid data
        return IngredientAnalysisResult(
            name=db_ingredient.name,
            alternate_names=[],
            is_found=True,
            id=db_ingredient.id,
            safety_rating=db_ingredient.safety_rating or 5,
            description=db_ingredient.description or "No description available",
            health_effects=["Unknown"],
            details_with_source=[]
        )


async def add_product_to_database(
    product_id: int,
    image_names: List[str],
    db: Session,
    product_data: Dict[str, Any],
):
    """
    Adds markers for the product, or updates it if it exists.
    """
    try:
        log_info(f"Adding markers to product with ID {product_id} in database")
        product_service = ProductService(db)
        product = product_service.get_product_by_id(product_id)
        if not product:
            raise Exception(f"Product with ID {product_id} not found")

        # Add or update markers for the product
        for image_name in image_names:
            image_path = os.path.join(UPLOADED_IMAGES_DIR, image_name)

            vuforia_id = await add_target_to_vuforia(image_name, image_path)
            existing_marker = db.query(Marker).filter_by(image_name=image_name, product_id=product.id).first()

            if not existing_marker:
                marker = Marker(image_name=image_name, vuforia_id=vuforia_id, product_id=product.id)
                db.add(marker)
            else:
                log_info(f"Marker {image_name} already exists for product {product_id}. Updating Vuforia ID.")
                existing_marker.vuforia_id = vuforia_id

        db.commit()
        log_info(f"Product markers added/updated successfully in database")
        return True
    except Exception as e:
        db.rollback()
        log_error(f"Error adding/updating markers for product {product_id} in database: {e}",e)
        raise HTTPException(status_code=500, detail=f"Error adding/updating markers for product {product_id}: {e}")