from typing import Dict, Any, Optional

def format_analysis_response(product_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
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

    # Assuming product_data is a dictionary representing the joined data from product, ingredients, etc.
    # Adjust field names based on your actual database schema and query results.
    safety_score_value = product_data.get("safety_score")
    safety_score_isPresent = safety_score_value is not None

    return {
        "found": True,
        "safety_score": {
            "calculated": safety_score_calculated,
            "value": safety_score_value,
        },
        "product_info": {
            "id": product_data.get("product_id"),
            "name": product_data.get("product_name"),
            "barcode": product_data.get("product_barcode"),
            "image_url": product_data.get("product_image_url"),
            "brand": product_data.get("product_brand"),
            "manufacturing_places": product_data.get("product_manufacturing_places"),
            "stores": product_data.get("product_stores"),
            "countries": product_data.get("product_countries"),
        } if product_data.get("product_id") is not None else None,
        "ingredient_info": {
            "ingredients_text": product_data.get("ingredients_text"),
            "ingredients_analysis": product_data.get("ingredients_analysis"),
            "additives": product_data.get("additives"),
        } if product_data.get("ingredients_text") is not None else None,
        "allergen_info": {
            "allergens": product_data.get("allergens"),
            "traces": product_data.get("traces"),
        } if product_data.get("allergens") is not None or product_data.get("traces") is not None else None,
        "diet_info": {
            "vegan": product_data.get("vegan"),
            "vegetarian": product_data.get("vegetarian"),
        } if product_data.get("vegan") is not None or product_data.get("vegetarian") is not None else None,
        "nutritional_info": product_data.get("nutritional_info"),  # Assuming this is already a dict
        "manufacturing_info": product_data.get("manufacturing_info"),  # Assuming this is already a dict
    }

# Add other helper functions as needed for analysis