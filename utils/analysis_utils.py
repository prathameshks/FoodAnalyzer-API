from typing import Dict, Any, Optional

def format_product_analysis_response(product_data) -> Dict[str, Any]:
    """
    Formats the retrieved product analysis data into a consistent response structure.

    Args:
        product_data: A dictionary containing product data, or None if not found.

    Returns:
        A dictionary representing the formatted response.
    """
    if product_data is None:
        return {
            "found": False,
            "safety_score": {"isPresent": False, "value": None},
            "product_info": None,
            "ingredient_info": None,
            "allergen_info": None,
            "diet_info": None,
            "nutritional_info": None,
            "manufacturing_info": None,
        }

    safety_score_value = product_data.safety_score
    safety_score_isPresent = safety_score_value is not None

    return {
        "found": True,
        "safety_score": {
            "isPresent": safety_score_isPresent,
            "value": safety_score_value,
        },
        "product_info": {
            "id": product_data.id,
            "name": product_data.name,
            "barcode": product_data.barcode,
            "image_url": product_data.image_url,
            "brand": product_data.brand,
            "manufacturing_places": product_data.manufacturing_places,
            "stores": product_data.stores,
            "countries": product_data.countries,
        } if product_data.id is not None else None,
        "ingredient_info": {
            "ingredients_text": product_data.ingredients_text,
            "ingredients_analysis": product_data.ingredients_analysis,
            "additives": product_data.additives,
        } if product_data.ingredients_text is not None else None,
        "allergen_info": {
            "allergens": product_data.allergens,
            "traces": product_data.traces,
        } if product_data.allergens is not None or product_data.traces is not None else None,
        "diet_info": {
            "vegan": product_data.get("vegan"),
            "vegetarian": product_data.get("vegetarian"),
        } if product_data.get("vegan") is not None or product_data.get("vegetarian") is not None else None,
        "nutritional_info": product_data.get("nutritional_info"),  # Assuming this is already a dict
        "manufacturing_info": product_data.get("manufacturing_info"),  # Assuming this is already a dict
    }

# Add other helper functions as needed for analysis