from fastapi import APIRouter, HTTPException
from utils import fetch_product_data_from_api
from models import ProductInfo

router = APIRouter()

@router.get("/extract_product_info", response_model=ProductInfo)
def extract_product_info(barcode: str):
    data = fetch_product_data_from_api(barcode)
    product = data.get('product', {})

    product_info = {
        "product_name": product.get('product_name_en', product.get('product_name', 'N/A')),
        "generic_name": product.get('generic_name_en', product.get('generic_name', 'N/A')),
        "brands": product.get('brands', 'N/A'),
        "ingredients": [],
        "ingredients_text": product.get('ingredients_text_en', product.get('ingredients_text', 'N/A')),
        "ingredients_analysis": product.get('ingredients_analysis', {}),
        "nutriscore": product.get('nutriscore', {}),
        "nutrient_levels": product.get('nutrient_levels', {}),
        "nutriments": product.get('nutriments', {}),
        "data_quality_warnings": product.get('data_quality_warnings_tags', [])
    }

    ingredients_list = product.get('ingredients', [])
    for ingredient in ingredients_list:
        ingredient_info = {
            "text": ingredient.get('text', 'N/A'),
            "percent": ingredient.get('percent', ingredient.get('percent_estimate', 'N/A')),
            "vegan": ingredient.get('vegan', 'N/A'),
            "vegetarian": ingredient.get('vegetarian', 'N/A'),
            "sub_ingredients": []
        }
        sub_ingredients = ingredient.get('ingredients', [])
        for sub_ingredient in sub_ingredients:
            sub_ingredient_info = {
                "text": sub_ingredient.get('text', 'N/A'),
                "percent": sub_ingredient.get('percent', sub_ingredient.get('percent_estimate', 'N/A')),
                "vegan": sub_ingredient.get('vegan', 'N/A'),
                "vegetarian": sub_ingredient.get('vegetarian', 'N/A')
            }
            ingredient_info["sub_ingredients"].append(sub_ingredient_info)
        product_info["ingredients"].append(ingredient_info)

    return product_info