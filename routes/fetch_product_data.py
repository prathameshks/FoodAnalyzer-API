from fastapi import APIRouter
from models import Barcodes
from utils import fetch_product_data_from_api, save_json_file

router = APIRouter()

@router.post("/fetch_product_data")
def fetch_product_data(barcodes: Barcodes):
    for item, barcode in barcodes.barcodes.items():
        data = fetch_product_data_from_api(barcode)
        save_json_file(item, data)
    return {"message": "Data fetched and saved successfully"}