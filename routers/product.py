import io
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from logger_manager import log_debug, log_info, log_error
from PIL import Image
import os
from services.product_service import ProductService
from db.models import Marker
from sqlalchemy.orm import Session
from db.database import get_db
from fastapi import Depends
from db.repositories import ProductRepository, IngredientRepository
from interfaces.productModels import ProductCreate
from typing import Generator
from dotenv import load_dotenv
import requests
import json
from services.ingredients import IngredientService 
from services.productAnalyzerAgent import analyze_product_ingredients
from utils.fetch_data import fetch_product_data_from_api

load_dotenv()

UPLOADED_IMAGES_DIR = "uploaded_images"
if not os.path.exists(UPLOADED_IMAGES_DIR):
    os.makedirs(UPLOADED_IMAGES_DIR)


VUFORIA_SERVER_ACCESS_KEY = os.getenv("VUFORIA_SERVER_ACCESS_KEY")
VUFORIA_SERVER_SECRET_KEY = os.getenv("VUFORIA_SERVER_SECRET_KEY")
VUFORIA_TARGET_DATABASE_NAME = os.getenv("VUFORIA_TARGET_DATABASE_NAME")
VUFORIA_TARGET_DATABASE_ID = os.getenv("VUFORIA_TARGET_DATABASE_ID")

router = APIRouter()


def get_vuforia_auth_headers():
    """
    Returns the authentication headers for Vuforia API requests.
    """
    return {
        "Authorization": f"VWS {VUFORIA_SERVER_ACCESS_KEY}:{VUFORIA_SERVER_SECRET_KEY}",
        "Content-Type": "application/json",
    }


async def add_target_to_vuforia(image_name: str, image_path: str) -> str:
    """
    Adds a target to the Vuforia database and returns the Vuforia target ID.
    """
    log_info(f"Adding target {image_name} to Vuforia")

    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()

        url = f"https://vws.vuforia.com/targets"

        headers = get_vuforia_auth_headers()
        payload = {
            "name": image_name,
            "width": 1.0,  # Default width
            "image": image_data.hex(),  # Convert image data to hex
            "active_flag": True,
        }

        response = await requests.post(url, headers=headers, json=payload)
        response_data = json.loads(response.text)
        if response.status_code == 201:
            log_info(
                f"Target {image_name} added successfully with Vuforia ID: {response_data['target_id']}"
            )
            return response_data["target_id"]
        else:
            log_error(f"Failed to add target {image_name}: {response.text}")
            raise Exception(f"Failed to add target {image_name}: {response.text}")
    except Exception as e:
        log_error(f"Error adding target {image_name}: {e}",e)
        raise


async def add_product_to_database(
    product_id: int,
    image_names: List[str],
    db: Session,
    product_data: Dict[str, Any],
):
    """
    Adds markers for the product, or updates it if it exists.
    """
    try:
        log_info(f"Adding markers to product with ID {product_id} in database")
        product_service = ProductService(db)
        product = product_service.get_product_by_id(product_id)
        if not product:
            raise Exception(f"Product with ID {product_id} not found")

        # Add or update markers for the product
        for image_name in image_names:
            image_path = os.path.join(UPLOADED_IMAGES_DIR, image_name)

            vuforia_id = await add_target_to_vuforia(image_name, image_path)
            existing_marker = db.query(Marker).filter_by(image_name=image_name, product_id=product.id).first()

            if not existing_marker:
                marker = Marker(image_name=image_name, vuforia_id=vuforia_id, product_id=product.id)
                db.add(marker)
            else:
                log_info(f"Marker {image_name} already exists for product {product_id}. Updating Vuforia ID.")
                existing_marker.vuforia_id = vuforia_id

        db.commit()
        log_info(f"Product markers added/updated successfully in database")
        return True
    except Exception as e:
        db.rollback()
        log_error(f"Error adding/updating markers for product {product_id} in database: {e}",e)
        raise HTTPException(status_code=500, detail=f"Error adding/updating markers for product {product_id}: {e}")


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