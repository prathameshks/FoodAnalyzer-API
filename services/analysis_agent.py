from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Dict, Any, List
from models.user_preferences import UserPreferences
from services.ingredients import get_ingredient_data, filter_ingredients_by_preferences
from models.ingredient import Ingredient
from services.logging_service import log_info, log_error

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
