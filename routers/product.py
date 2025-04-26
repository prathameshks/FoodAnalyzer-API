import io
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from logger_manager import log_info, log_error
from PIL import Image
import os
from services.product_service import ProductService
from db.models import Marker, Ingredient
from sqlalchemy.orm import Session
from db.database import get_db
from fastapi import Depends
from typing import Generator
from dotenv import load_dotenv
import requests
import json
from services.ingredients import IngredientService

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
        log_error(f"Error adding target {image_name}: {e}")
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
        log_error(f"Error adding/updating markers for product {product_id} in database: {e}")
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
        product_id = data.get("product_id")

        image_names: List[str] = data.get("image_names")

        product_data = {
            "ingredients_text": data.get("ingredients_text", ""),
            "brands": data.get("brands", ""),
            "generic_name": data.get("generic_name", ""),
            "nutriscore": data.get("nutriscore", None),
            "nutrient_levels": data.get("nutrient_levels", None),
            "nutriments": data.get("nutriments", None),
            "data_quality_warnings": data.get("data_quality_warnings", None),
        }
        product_service = ProductService(db)
        if not product_id:
            product = product_service.add_product(data.get("name"), product_data["ingredients_text"])
            product_id = product.id
        await add_product_to_database(product_id, image_names, db, product_data)
        return JSONResponse(
            {"message": "Product data and image processed successfully"}
        )

    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)
    except Exception as e:
         return JSONResponse({"error": str(e)}, status_code=500)
