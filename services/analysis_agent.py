from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Dict, Any, List
from models.user_preferences import UserPreferences
from services.ingredients import get_ingredient_data, filter_ingredients_by_preferences
from models.ingredient import Ingredient

def analyze_ingredients(db: Session, ingredients: List[Dict[str, Any]], user_id: int) -> Dict[str, Any]:
    preferences = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    if not preferences:
        raise HTTPException(status_code=404, detail="User preferences not found")

    filtered_ingredients = filter_ingredients_by_preferences(ingredients, preferences.__dict__)
    analysis_results = {
        "safe_ingredients": [],
        "unsafe_ingredients": [],
        "additional_facts": []
    }

    for ingredient in filtered_ingredients:
        ingredient_data = get_ingredient_data(db, ingredient["text"])
        if ingredient_data:
            analysis_results["safe_ingredients"].append({
                "name": ingredient["text"],
                "nutritional_info": ingredient_data
            })
        else:
            analysis_results["unsafe_ingredients"].append({
                "name": ingredient["text"],
                "reason": "Information not found"
            })

    return analysis_results

def provide_personalized_recommendations(db: Session, user_id: int) -> Dict[str, Any]:
    preferences = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    if not preferences:
        raise HTTPException(status_code=404, detail="User preferences not found")

    recommended_ingredients = []
    all_ingredients = db.query(Ingredient).all()
    for ingredient in all_ingredients:
        if ingredient.name not in preferences.disliked_ingredients:
            recommended_ingredients.append({
                "name": ingredient.name,
                "nutritional_info": ingredient.nutritional_info
            })

    return {"recommended_ingredients": recommended_ingredients}
