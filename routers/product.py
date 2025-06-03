from datetime import datetime
import io
from fastapi import APIRouter, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Any
from logger_manager import log_debug, log_info, log_error
import os
from services.auth_service import get_current_user
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



from services.ingredients import IngredientService 
from services.productAnalyzerAgent import analyze_product_ingredients
from utils.analyze import process_product_ingredients
from utils.db_utils import add_product_to_database
from utils.fetch_data import fetch_product_data_from_api
import uuid
import json

# import environment variables
from env import FAKE_TARGET_IMAGE_NAME, SEND_FAKE_TARGET,UPLOADED_IMAGES_DIR, VUFORIA_SERVER_ACCESS_KEY,VUFORIA_SERVER_SECRET_KEY,VUFORIA_TARGET_DATABASE_NAME,VUFORIA_TARGET_DATABASE_ID

router = APIRouter()


TARGET_CLASSES = set(["Food processor", "Fast food", "Food", "Seafood", "Snack"])

def run_object_detection(image: Image.Image, request: Request):
    # Access the model from app state
    detector = request.app.state.detector
    image_np = np.array(image)
    input_tensor = tf.convert_to_tensor(image_np)[tf.newaxis, ...]
    input_tensor = tf.cast(input_tensor, tf.float32) / 255.0
    results = detector(input_tensor)
    results = {k: v.numpy() for k, v in results.items()}
    return results, image_np

def get_filtered_class_boxes(results):
    # for same class, keep the one with the highest score
    # and remove duplicates
    high_boxes = None
    high_classes = None
    high_scores = None

    for i in range(len(results["detection_scores"])):
        class_name = results["detection_class_entities"][i].decode("utf-8")
        box = results["detection_boxes"][i]
        score = results["detection_scores"][i]
        if class_name in TARGET_CLASSES:
            if high_boxes is None:
                high_boxes = box
                high_classes = class_name
                high_scores = score
            else:
                if score > high_scores:
                    high_boxes = box
                    high_classes = class_name
                    high_scores = score
    return high_boxes, high_classes, high_scores

def crop_image(image_np, box):
    ymin, xmin, ymax, xmax = box
    im_width, im_height = image_np.shape[1], image_np.shape[0]
    (left, right, top, bottom) = (xmin * im_width, xmax * im_width,
                                    ymin * im_height, ymax * im_height)
    cropped_image = image_np[int(top):int(bottom), int(left):int(right)]
    return Image.fromarray(cropped_image)




@router.post("/add")
async def create_product(
    request: Request,
    db: Session = Depends(get_db)
):
    """Endpoint to add a new product, its ingredients, and associated markers."""
    try:
        log_info("Create product endpoint called")
        # Get the request body
        form_data = await request.form()
        name = form_data.get("name")
        image_name = form_data.get("image_name")

        # Extract all ingredients[] fields as a list
        ingredients_list = []
        for key, value in form_data.multi_items():
            if key == "ingredients[]":
                ingredients_list.append(value)
                
        log_debug(f"Received product name: {name}")
        log_debug(f"Received ingredients: {ingredients_list}")
        log_debug(f"Received image name: {image_name}")
            
        # Save the uploaded image
        image_path = os.path.join(UPLOADED_IMAGES_DIR, image_name)

        # analyze the product ingredients
        results = await process_product_ingredients(ingredients_list)
        
        # extract data from the analysis results 
        #         result = {
        #     "ingredients_count": len(product_ingredients),
        #     "processed_ingredients": ingredient_results,
        #     "ingredient_ids": product_analysis["ingredient_ids"],
        #     "overall_analysis": product_analysis,
        #     "timestamp": datetime.now(tz=pytz.timezone('Asia/Kolkata')).isoformat()
        # }
        # {{
        # "overall_safety_score": (number between 1-10),
        # "suitable_diet_types": (strings from "Vegan", "Vegetarian", "Non-Vegetarian"),
        # "allergy_warnings": (array of strings),
        # "usage_recommendations": (string with specific guidance),
        # "health_insights": {{
        # "benefits": (array of strings),
        # "concerns": (array of strings)
        # }},
        # "ingredient_interactions": (array of strings),
        # "key_takeaway": (string)
        # }}
        
        # Check if the analysis results are valid
        analysis_results = results.get("overall_analysis", {})
        overall_safety_score = analysis_results.get("overall_safety_score", 0)
        suitable_diet_types = analysis_results.get("suitable_diet_types", [])
        allergy_warnings = analysis_results.get("allergy_warnings", [])
        usage_recommendations = analysis_results.get("usage_recommendations", "")
        health_insights = analysis_results.get("health_insights", {})
        ingredient_interactions = analysis_results.get("ingredient_interactions", [])
        key_takeaway = analysis_results.get("key_takeaway", "")
        
        current_user_id = 0
        try:
            current_user = await get_current_user()
            current_user_id = current_user.id
        except:
            # Handle case where user is not authenticated
            log_error("User not authenticated, using default user ID")
            current_user_id = 0  # Default user ID, change as needed
        
        # Create product data model
        product_create_data = ProductCreate(
            product_name=name,
            ingredients=json.dumps(ingredients_list),
            overall_safety_score=overall_safety_score,
            suitable_diet_types=json.dumps(suitable_diet_types),
            allergy_warnings=json.dumps(allergy_warnings),
            usage_recommendations=usage_recommendations,
            health_insights=json.dumps(health_insights),
            ingredient_interactions=json.dumps(ingredient_interactions),
            key_takeaway=json.dumps(key_takeaway),
            ingredients_count=results.get("ingredients_count", 0),
            user_id=current_user_id,  # Can be updated later if needed
            timestamp=results.get("timestamp", datetime.now().isoformat()),
            ingredient_ids=json.dumps(results.get("ingredient_ids", [])),
        )


        # Add product to database
        product_repo = ProductRepository(db)
        product = product_repo.add_product(product_create_data)
        
        print(product)
        
        # Add Vuforia target if needed
        await add_product_to_database(product.id, [image_name], db, {
            "name": name,
            "ingredients": ingredients_list,
            "image_name": image_name,
        })
        
        return JSONResponse({
            "message": "Product data and image processed successfully",
            "product_id": product.id,
            "image_name": image_name
        })
    except Exception as e:
        log_error(f"Error creating product: {e}", e)
        print(e)
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/process_image")
async def process_image_endpoint(image: UploadFile = File(...), db: Session = Depends(get_db), request: Request = None):
    """
    Receives an image file, performs object detection, and returns information about detected objects.
    """
    log_info("Process image endpoint called")
    try:
        # Read image from the uploaded file
        image_data = await image.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # Run object detection with the request object
        results, image_np = run_object_detection(image, request)

        # Get filtered class boxes
        box, class_name, score = get_filtered_class_boxes(results)
        
        # Check if any objects were detected
        if box is None:
            log_info("No food objects detected in image")
            # if send dummy target is allowed send default image
            if SEND_FAKE_TARGET:
                return JSONResponse({
                    "class_name": "food",
                    "score": float(0.24),
                    "image_name": FAKE_TARGET_IMAGE_NAME,
                    "detected": True
                })
            return JSONResponse({
                "error": "No food objects detected in the image",
                "detected": False
            }, status_code=400)

        # Crop the detected object
        cropped_img = crop_image(image_np, box)

        # Save the cropped image temporarily
        unique_id = uuid.uuid4().hex
        cropped_image_name = f"detected_{class_name}_{score:.2f}_{unique_id}.jpg"
        cropped_image_path = os.path.join(
            UPLOADED_IMAGES_DIR, cropped_image_name
        )
        cropped_img.save(cropped_image_path)

        return JSONResponse({
            "class_name": class_name,
            "score": float(score),
            "image_name": cropped_image_name,
            "detected": True
        })
    except Exception as e:
        log_error(f"Error processing image: {e}", e)
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
        
    
# In your API, add an endpoint like:
@router.get("/marker/{vuforia_id}")
async def get_product_by_marker(vuforia_id: str, db: Session = Depends(get_db)):
    marker = db.query(Marker).filter(Marker.vuforia_id == vuforia_id).first()
    if not marker:
        raise HTTPException(status_code=404, detail="Target not found")
    
    product = db.query(Product).filter(Product.id == marker.product_id).first()
    return product