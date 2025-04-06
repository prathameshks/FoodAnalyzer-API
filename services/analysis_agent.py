from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Dict, Any, List
from models.user_preferences import UserPreferences
from services.ingredients import get_ingredient_data, filter_ingredients_by_preferences
from models.ingredient import Ingredient
from services.logging_service import log_info, log_error
from langchain.llms import OpenAI

def provide_personalized_recommendations(db: Session, user_id: int) -> Dict[str, Any]:
    log_info("provide_personalized_recommendations function called")
    try:
        preferences = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
        if not preferences:
            log_error("User preferences not found")
            raise HTTPException(status_code=404, detail="User preferences not found")

        recommended_ingredients = []
        all_ingredients = db.query(Ingredient).all()
        for ingredient in all_ingredients:
            if ingredient.name not in preferences.disliked_ingredients:
                recommended_ingredients.append({
                    "name": ingredient.name,
                    "nutritional_info": ingredient.nutritional_info
                })

        log_info("provide_personalized_recommendations function completed successfully")
        return {"recommended_ingredients": recommended_ingredients}
    except Exception as e:
        log_error(f"Error in provide_personalized_recommendations function: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def analyze_ingredients(ingredients: List[str]) -> List[Dict[str, Any]]:
    log_info("analyze_ingredients function called")
    try:
        analysis_results = []
        for ingredient in ingredients:
            safety_score = OpenAI().analyze_safety(ingredient)
            score = OpenAI().analyze_score(ingredient)
            eating_limit = OpenAI().analyze_eating_limit(ingredient)
            key_insights = OpenAI().analyze_key_insights(ingredient)
            analysis_results.append({
                "ingredient": ingredient,
                "safety": safety_score,
                "score": score,
                "eating_limit": eating_limit,
                "key_insights": key_insights
            })
        log_info("analyze_ingredients function completed successfully")
        return analysis_results
    except Exception as e:
        log_error(f"Error in analyze_ingredients function: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
