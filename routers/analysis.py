from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from database import get_db
from models.user import User
from models.ingredient import Ingredient
from models.product import Product
from services.auth_service import get_current_user
from services.ai_agent import process_data, process_ingredients

router = APIRouter()

@router.get("/personalized_recommendations")
def personalized_recommendations_endpoint(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        recommendations = provide_personalized_recommendations(db, current_user.id)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process_product")
def process_product_endpoint(barcode: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        product_data = process_data(db, barcode)
        return product_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process_ingredients")
def process_ingredients_endpoint(ingredients: List[str], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        result = process_ingredients(db, ingredients, current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
