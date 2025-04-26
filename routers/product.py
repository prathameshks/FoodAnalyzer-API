import io
from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse
from typing import List
from logger_manager import log_info, log_error
from fastapi.encoders import jsonable_encoder
from PIL import Image
import os
import uuid

UPLOADED_IMAGES_DIR = "uploaded_images"
if not os.path.exists(UPLOADED_IMAGES_DIR):
    os.makedirs(UPLOADED_IMAGES_DIR)

router = APIRouter()


@router.post("/add")
async def create_product(
    request: Request, image: UploadFile = File(...)
):  # Changed to accept pre-processed image
    log_info("Create product endpoint called")
    try:
        data = await request.json()
        print("Received data:", data)

        # Extract product details from the request body
        name = data.get("name")
        ingredients: List[str] = data.get("ingredients")
        image_path: str = data.get("image_path")

        # TODO actual adding product to DB and Vuforia Target linking 
        print("Product Name:", name)
        print("Ingredients:", ingredients)
        print("Image_path:", image_path)
        return JSONResponse(
            {"message": "Product data and image received and processed successfully"}
        )

    except Exception as e:
        print("Error:", e)
        return JSONResponse({"error": str(e)}, status_code=500)
