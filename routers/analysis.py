from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from database import get_db
from models.user import User
from models.ingredient import Ingredient
from models.product import Product
from services.auth_service import get_current_user
from services.ai_agent import process_data, process_ingredients
from services.logging_service import log_info, log_error

router = APIRouter()

@router.get("/personalized_recommendations")
def personalized_recommendations_endpoint(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log_info("personalized_recommendations_endpoint called")
    try:
        recommendations = provide_personalized_recommendations(db, current_user.id)
        log_info("personalized_recommendations_endpoint completed successfully")
        return recommendations
    except Exception as e:
        log_error(f"Error in personalized_recommendations_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process_product")
def process_product_endpoint(barcode: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log_info("process_product_endpoint called")
    try:
        product_data = process_data(db, barcode)
        log_info("process_product_endpoint completed successfully")
        return product_data
    except Exception as e:
        log_error(f"Error in process_product_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process_ingredients")
def process_ingredients_endpoint(ingredients: List[str], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log_info("process_ingredients_endpoint called")
    print(ingredients)
    try:
        result = process_ingredients(db, ingredients, current_user.id)
        log_info("process_ingredients_endpoint completed successfully")
        return result
    except Exception as e:
        log_error(f"Error in process_ingredients_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
