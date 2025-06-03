from typing import Dict, Any, Optional, Any
from interfaces.productModels import ProductAnalysisResponse

def format_product_analysis_response(product_data: Optional[Any]) -> Optional[ProductAnalysisResponse]:
    """
    Formats the retrieved product analysis data into a consistent response structure.

    Args:
        product_data: A SQLAlchemy Product object, or None if not found.

    Returns:
        A ProductAnalysisResponse object or None.
    """
    if product_data is None:
        return None

    # Assuming product_data is a SQLAlchemy Product object
    safety_score_value = product_data.overall_safety_score
    safety_score_isPresent = safety_score_value is not None

    return ProductAnalysisResponse(
        found=True,
        safety_score={
            "isPresent": safety_score_isPresent,
            "value": safety_score_value,
        },
        product_info= {
            "id": product_data.id,
            "name": product_data.product_name,
            "barcode": None, # Assuming barcode is not in Product model
            "image_url": None, # Assuming image_url is not in Product model
            "brand": None, # Assuming brand is not in Product model
            "manufacturing_places": None, # Assuming manufacturing_places is not in Product model
            "stores": None, # Assuming stores is not in Product model
            "countries": None, # Assuming countries is not in Product model
        },
        ingredient_info={
            "ingredients_text": product_data.ingredients,
            "ingredients_analysis": product_data.ingredient_interactions, # Assuming ingredient_interactions maps to analysis
            "additives": None, # Assuming additives are not directly in Product model
        },
        allergen_info= {
            "allergens": product_data.allergy_warnings,
            "traces": None, # Assuming traces are not directly in Product model
        },
        diet_info={
            "vegan": None, # Assuming vegan is not directly in Product model
            "vegetarian": None, # Assuming vegetarian is not directly in Product model
        },
        nutritional_info=None, # Assuming nutritional_info is not directly in Product model
        manufacturing_info=None # Assuming manufacturing_info is not directly in Product model
    )

# Add other helper functions as needed for analysis