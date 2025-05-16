import requests
from fastapi import HTTPException

async def fetch_product_data_from_api(barcode):
    url = f"https://india.openfoodfacts.org/api/v2/product/{barcode}.json"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch data for barcode {barcode}")
    return response.json()

def extract_product_info(product_data: dict):
    """
    Extracts product information (found status, name, ingredients) from OpenFoodFacts API response.
    """
    found = product_data.get('status') == 1
    product = product_data.get('product')

    if not found or not product:
        return False, None, []

    name = product.get('product_name')
    ingredients = []
    ingredients_list = product.get('ingredients', [])
    for ingredient in ingredients_list:
        ingredients.append(ingredient.get('text'))
    return found, name, ingredients
