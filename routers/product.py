import io
from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse
from typing import List, Dict
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
async def create_product(request: Request, image: UploadFile = File(...)):
    log_info("Create product endpoint called")
    try:
        data = await request.json()
        print("Received data:", data)
        
        # dummy code below save image target to Vuforia and other details with id from vuforia
        # TODO: Implement Vuforia integration to save image target and retrieve ID
        # For now, we will just print the data and save the image locally
        # Extract product details from the request body

        name = data.get("name")
        ingredients: List[str] = data.get("ingredients")

        print("Product Name:", name)
        print("Ingredients:", ingredients)

        # Save the uploaded image
        image_filename = f"{uuid.uuid4()}.jpg"  # Generate a unique filename
        image_path = os.path.join(UPLOADED_IMAGES_DIR, image_filename)
        

        contents = await image.read()
        img = Image.open(io.BytesIO(contents))
        img.save(image_path, "JPEG")

        print("Image saved to:", image_path)

        return JSONResponse({"message": "Product data and image received and processed successfully"})

    except Exception as e:
        print("Error:", e)
        return JSONResponse({"error": str(e)}, status_code=500)