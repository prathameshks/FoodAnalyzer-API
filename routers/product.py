import io
from fastapi import APIRouter, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Any
from logger_manager import log_debug, log_info, log_error
import os
from services.product_service import ProductService
from db.models import Marker, Product
from sqlalchemy.orm import Session
from interfaces.productModels import ProductCreate
from typing import Generator
import numpy as np
import tensorflow as tf # Ensure TensorFlow is imported
import tensorflow_hub as hub
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO # Keep BytesIO as it's used with PIL

from db.database import get_db
from fastapi import Depends
from db.repositories import ProductRepository, IngredientRepository

from dotenv import load_dotenv


from services.ingredients import IngredientService 
from services.productAnalyzerAgent import analyze_product_ingredients
from utils.fetch_data import fetch_product_data_from_api


load_dotenv()


UPLOADED_IMAGES_DIR = "uploaded_images"
if not os.path.exists(UPLOADED_IMAGES_DIR):
    os.makedirs(UPLOADED_IMAGES_DIR)


# TensorFlow model caching
detector = None


def load_detector():
    global detector
    if detector is None:
        detector = hub.load("https://tfhub.dev/google/openimages_v4/ssd/mobilenet_v2/1").signatures['default']

VUFORIA_SERVER_ACCESS_KEY = os.getenv("VUFORIA_SERVER_ACCESS_KEY")
VUFORIA_SERVER_SECRET_KEY = os.getenv("VUFORIA_SERVER_SECRET_KEY")
VUFORIA_TARGET_DATABASE_NAME = os.getenv("VUFORIA_TARGET_DATABASE_NAME")
VUFORIA_TARGET_DATABASE_ID = os.getenv("VUFORIA_TARGET_DATABASE_ID")

router = APIRouter()


TARGET_CLASSES = set(["Food processor", "Fast food", "Food", "Seafood", "Snack"])

def run_object_detection(image: Image.Image):
    load_detector()  # Ensure model is loaded
    image_np = np.array(image)
    # Convert to tensor without specifying dtype
    input_tensor = tf.convert_to_tensor(image_np)[tf.newaxis, ...]
    # Convert to float32 and normalize to [0,1]
    input_tensor = tf.cast(input_tensor, tf.float32) / 255.0
    results = detector(input_tensor)
    results = {k: v.numpy() for k, v in results.items()}
    return results, image_np

def get_filtered_class_boxes(results):
    # for same class, keep the one with the highest score
    # and remove duplicates
    boxes = []
    classes = []
    scores = []

    for i in range(len(results["detection_scores"])):
        class_name = results["detection_class_entities"][i].decode("utf-8")
        box = results["detection_boxes"][i]
        score = results["detection_scores"][i]
        if class_name in TARGET_CLASSES:
            if class_name not in classes:
                boxes.append(box)
                classes.append(class_name)
                scores.append(score)
            else:
                index = classes.index(class_name)
                if score > scores[index]:
                    boxes[index] = box
                    classes[index] = class_name
                    scores[index] = score
    return boxes, classes, scores

def crop_image(image_np, box):
    ymin, xmin, ymax, xmax = box
    im_width, im_height = image_np.shape[1], image_np.shape[0]
    (left, right, top, bottom) = (xmin * im_width, xmax * im_width,
                                    ymin * im_height, ymax * im_height)
    cropped_image = image_np[int(top):int(bottom), int(left):int(right)]
    return Image.fromarray(cropped_image)




@router.post("/add")
async def create_product(
    request: Request, db: Session = Depends(get_db)
):
    """Endpoint to add a new product, its ingredients, and associated markers."""
    try:
        log_info("Create product endpoint called")
        data = await request.json()
        print("Received data:", data)

        # Extract product details and data from request body
        
        image_names: List[str] = data.get("image_names")
        
        # Parse ProductCreate model from data
        product_create_data = ProductCreate(
            product_name=data.get("name"),
            ingredients=data.get("ingredients"),
            overall_safety_score=data.get("overall_safety_score"),
            suitable_diet_types=data.get("suitable_diet_types"),
            allergy_warnings=data.get("allergy_warnings"),
            usage_recommendations=data.get("usage_recommendations"),
            health_insights=data.get("health_insights"),
            ingredient_interactions=data.get("ingredient_interactions"),
            key_takeaway=data.get("key_takeaway"),
            ingredients_count=data.get("ingredients_count"),
            user_id=data.get("user_id"),
            timestamp=data.get("timestamp"),
            ingredient_ids=[]  
        )

        # Find ingredients and append their IDs
        ingredient_repo = IngredientRepository(db)
        for ingredient_name in product_create_data.ingredients:
            ingredient = ingredient_repo.get_ingredient_by_name(ingredient_name)
            if ingredient:
                product_create_data.ingredient_ids.append(ingredient.id)

        # Analyze product ingredients and store analysis data
        ingredient_results = []
        for ingredient_name in product_create_data.ingredients:
            ingredient = ingredient_repo.get_ingredient_by_name(ingredient_name)
            if ingredient:
                ingredient_results.append(ingredient)
        
        product_analysis = await analyze_product_ingredients(
            ingredients_data=ingredient_results,
            user_preferences={
                "user_id": product_create_data.user_id,
                "allergies": None,
                "dietary_restrictions": None
            }
        )
        product_create_data.ingredients_analysis = product_analysis

        # use repository to add product
        product_repo = ProductRepository(db)
        product = product_repo.add_product(product_create_data)
        product_id=product.id
        await add_product_to_database(product_id, image_names, db, data)
        return JSONResponse(
            {
                 "message": "Product data and image processed successfully",
                "product_id":product_id,
                 "data":data,
                "product_data": product_create_data.model_dump()
                
             }
        )

    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)
    except Exception as e:
         return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/process_image")
async def process_image_endpoint(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Receives an image file, performs object detection, and returns information about detected objects.
    """
    log_info("Process image endpoint called")
    try:
        # Read image from the uploaded file
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # Run object detection
        results, image_np = run_object_detection(image)

        # Get filtered class boxes
        boxes, class_names, scores = get_filtered_class_boxes(results)

        detected_objects = []
        for i in range(len(boxes)):
            # Crop the detected object
            cropped_img = crop_image(image_np, boxes[i])

            # Save the cropped image temporarily
            cropped_image_path = os.path.join(UPLOADED_IMAGES_DIR, f"detected_{class_names[i]}_{scores[i]:.2f}.jpg")
            cropped_img.save(cropped_image_path)

            # Find if a product with this image exists in the database
            product_repo = ProductRepository(db)
            product = product_repo.get_product_by_image_name(os.path.basename(cropped_image_path))

            detected_objects.append({
                "class_name": class_names[i],
                "score": float(scores[i]),
                "product_info": product.to_dict() if product else None  # Assuming Product model has a to_dict method
            })

        return JSONResponse({"detected_objects": detected_objects})
    except Exception as e:
        log_error(f"Error processing image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing image: {e}")


@router.get("/find_barcode")
async def find_product_by_barcode(barcode_number: str):
    """Endpoint to find product data using a barcode number."""
    log_info(f"Find product by barcode endpoint called for barcode: {barcode_number}")
    try:
        product_data = await fetch_product_data_from_api(barcode_number)
        
        from utils.fetch_data import extract_product_info  # Import here to avoid circular dependency if utils imports routers
        
        found, product_name, ingredients = extract_product_info(product_data)

        if found:
            return JSONResponse({"found": found, "product_name": product_name, "ingredients": ingredients})
        else:
            return JSONResponse({"found": found, "product_name": None, "ingredients": []}, status_code=404)
            # Or raise HTTPException if you prefer
            raise HTTPException(status_code=404, detail=f"Product not found for barcode: {barcode_number}")
    except Exception as e:
        log_error(f"Error fetching product data for barcode {barcode_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching product data: {e}")


@router.get("/get_image/{image_name}")
async def get_image(image_name: str):
    """Endpoint to retrieve an image by its name."""
    image_path = os.path.join(UPLOADED_IMAGES_DIR, image_name)
    if os.path.exists(image_path):
        return FileResponse(image_path, media_type="image/jpeg")
    else:
        return JSONResponse({"error": "Image not found"}, status_code=404)