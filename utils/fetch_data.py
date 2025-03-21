import requests
from fastapi import HTTPException

def fetch_product_data_from_api(barcode):
    url = f"https://india.openfoodfacts.org/api/v2/product/{barcode}.json"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch data for barcode {barcode}")
    return response.json()
