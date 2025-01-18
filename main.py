from fastapi import FastAPI
from routes.extract_product_info_from_barcode import router as extract_product_info_router
from routes.fetch_product_data import router as fetch_product_data_router

app = FastAPI()

app.include_router(extract_product_info_router, prefix="/api")
app.include_router(fetch_product_data_router, prefix="/api")

# To run the FastAPI app, use the command: uvicorn main:app --reload