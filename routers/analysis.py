from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from database import get_db
from models.user import User
from models.ingredient import Ingredient
from services.analysis_agent import analyze_ingredients, provide_personalized_recommendations
from services.auth_service import get_current_user

router = APIRouter()

@router.post("/analyze_ingredients")
def analyze_ingredients_endpoint(ingredients: List[Dict[str, Any]], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        analysis_results = analyze_ingredients(db, ingredients, current_user.id)
        return analysis_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/personalized_recommendations")
def personalized_recommendations_endpoint(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        recommendations = provide_personalized_recommendations(db, current_user.id)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
