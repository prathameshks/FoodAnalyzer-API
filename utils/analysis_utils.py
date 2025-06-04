import json
from datetime import datetime
import pytz
from typing import Dict, Any, List, Optional
from db.models import Product
from interfaces.productModels import ProductAnalysisResponse
from logger_manager import log_info, log_error, log_debug

def safe_parse_json(value, default=None):
    """Safely parse a JSON string, with fallback to default value"""
    if value is None:
        return default
    
    if not isinstance(value, str):
        return value
        
    try:
        # Handle double-quoted JSON strings (e.g. '"Vegetarian"')
        parsed = json.loads(value)
        return parsed
    except json.JSONDecodeError:
        # If it's not valid JSON but might be a comma-separated list
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        return default

def format_product_analysis_response(product):
    """
    Format product data into a ProductAnalysisResponse object with simple error handling.
    """
    try:
        # Print product data for debugging
        log_debug(f"Product object attributes: {dir(product)}")
        log_debug(f"Product __dict__: {product.__dict__}")
        
        # Extract and parse the dietary flags - handle the specific case that's failing
        dietary_flags = []
        try:
            diet_types = getattr(product, 'suitable_diet_types', None)
            if diet_types:
                # Parse the JSON string - handle the case where it's a quoted string like '"Vegetarian"'
                parsed_diet = safe_parse_json(diet_types, [])
                if isinstance(parsed_diet, str):
                    dietary_flags = [parsed_diet]  # Convert single string to list
                elif isinstance(parsed_diet, list):
                    dietary_flags = parsed_diet
        except Exception as e:
            log_error(f"Error parsing dietary flags: {e}")
            dietary_flags = []
        
        # Parse health insights
        health_insights = {}
        try:
            insights_str = getattr(product, 'health_insights', None)
            if insights_str:
                health_insights = safe_parse_json(insights_str, {})
        except Exception as e:
            log_error(f"Error parsing health insights: {e}")
        
        # Extract warnings and benefits from health insights if available
        warnings = []
        benefits = []
        try:
            if isinstance(health_insights, dict):
                warnings = health_insights.get('concerns', [])
                benefits = health_insights.get('benefits', [])
        except Exception as e:
            log_error(f"Error extracting warnings/benefits: {e}")
        
        # Parse allergy warnings
        allergens = []
        try:
            allergy_str = getattr(product, 'allergy_warnings', None)
            if allergy_str:
                allergens = safe_parse_json(allergy_str, [])
        except Exception as e:
            log_error(f"Error parsing allergens: {e}")
        
        # Parse ingredients list
        ingredients_list = []
        try:
            ing_list = getattr(product, 'ingredients_list', None) or getattr(product, 'ingredients', None)
            if ing_list:
                ingredients_list = safe_parse_json(ing_list, [])
        except Exception as e:
            log_error(f"Error parsing ingredients list: {e}")
        
        # Parse ingredients analysis if available
        ingredients_analysis = []
        try:
            ing_analysis = getattr(product, 'ingredients_analysis', [])
            if ing_analysis:
                if isinstance(ing_analysis, list):
                    ingredients_analysis = ing_analysis
                else:
                    ingredients_analysis = safe_parse_json(ing_analysis, [])
        except Exception as e:
            log_error(f"Error parsing ingredients analysis: {e}")
        
        # Parse ingredient interactions
        ingredient_interactions = []
        try:
            interactions_str = getattr(product, 'ingredient_interactions', None)
            if interactions_str:
                ingredient_interactions = safe_parse_json(interactions_str, [])
        except Exception as e:
            log_error(f"Error parsing ingredient interactions: {e}")
            ingredient_interactions = []
        
        # Get usage recommendations
        usage_recommendations = ""
        try:
            usage_recommendations = getattr(product, 'usage_recommendations', "")
            if usage_recommendations and isinstance(usage_recommendations, str):
                if usage_recommendations.startswith('"') and usage_recommendations.endswith('"'):
                    usage_recommendations = safe_parse_json(usage_recommendations, "")
            if not isinstance(usage_recommendations, str):
                usage_recommendations = str(usage_recommendations)
        except Exception as e:
            log_error(f"Error parsing usage recommendations: {e}")
            usage_recommendations = ""
        
        # Get key takeaway
        key_takeaway = ""
        try:
            key_takeaway = getattr(product, 'key_takeaway', "")
            if key_takeaway and isinstance(key_takeaway, str):
                if key_takeaway.startswith('"') and key_takeaway.endswith('"'):
                    key_takeaway = safe_parse_json(key_takeaway, "")
            if not isinstance(key_takeaway, str):
                key_takeaway = str(key_takeaway)
        except Exception as e:
            log_error(f"Error parsing key takeaway: {e}")
            key_takeaway = ""
        
        # Construct the final response
        return ProductAnalysisResponse(
            found=True,
            basic_info={
                "product_id": str(product.id),
                "product_name": getattr(product, 'product_name', ''),
                "brand": "",
                "category": "",
                "image_url": None,
                "barcode": None
            },
            safety_info={
                "safety_score": float(getattr(product, 'overall_safety_score', 0)),
                "is_safe": getattr(product, 'overall_safety_score', 0) > 5,
                "warnings": warnings,
                "benefits": benefits
            },
            ingredient_info={
                "ingredients_list": ingredients_list,
                # "ingredients_analysis": ingredients_analysis,
                "ingredient_count": getattr(product, 'ingredients_count', 0)
            },
            allergen_info={
                "allergens": allergens,
                "has_allergens": len(allergens) > 0
            },
            dietary_info={
                "dietary_flags": dietary_flags,
                "is_vegetarian": any(flag.lower() == 'vegetarian' for flag in dietary_flags),
                "is_vegan": any(flag.lower() == 'vegan' for flag in dietary_flags)
            },
            recommendations_info={
                "usage_recommendations": usage_recommendations,
                "ingredient_interactions": ingredient_interactions,
                "key_takeaway": key_takeaway
            },
            timestamp=datetime.now(tz=pytz.timezone('Asia/Kolkata')).isoformat()
        )
    except Exception as e:
        log_error(f"Error in format_product_analysis_response: {str(e)}")
        # Return a minimal valid response rather than raising an exception
        return ProductAnalysisResponse(
            found=True,
            basic_info={
                "product_id": str(product.id),
                "product_name": getattr(product, 'product_name', 'Unknown Product'),
                "brand": "",
                "category": "",
                "image_url": None,
                "barcode": None
            },
            safety_info={
                "safety_score": 0.0,
                "is_safe": False,
                "warnings": [],
                "benefits": []
            },
            ingredient_info={
                "ingredients_list": [],
                # "ingredients_analysis": [],
                "ingredient_count": 0
            },
            allergen_info={
                "allergens": [],
                "has_allergens": False
            },
            dietary_info={
                "dietary_flags": [],
                "is_vegetarian": False,
                "is_vegan": False
            },
            recommendations_info={
                "usage_recommendations": "",
                "ingredient_interactions": [],
                "key_takeaway": ""
            },
            timestamp=datetime.now(tz=pytz.timezone('Asia/Kolkata')).isoformat()
        )