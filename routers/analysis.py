from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from interfaces.ingredientModels import IngredientAnalysisResult, IngredientRequest
from services.auth_service import get_current_user
from logger_manager import log_info, log_error,logger
from db.database import get_db
from db.repositories import IngredientRepository

from services.ingredientFinderAgent import IngredientInfoAgentLangGraph


router = APIRouter()

def ingredient_db_to_pydantic(db_ingredient):
    """Convert a database ingredient model to a Pydantic model."""
    return IngredientAnalysisResult(
        name=db_ingredient.name,
        alternate_names=db_ingredient.alternate_names or [],
        is_found=True,
        safety_rating=db_ingredient.safety_rating or 5,
        description=db_ingredient.description or "No description available",
        health_effects=db_ingredient.health_effects or ["Unknown"],
        details_with_source=[source.data for source in db_ingredient.sources]
    )


# process single ingredient 
@router.post("/process_ingredient", response_model=IngredientAnalysisResult)
async def process_ingredient_endpoint(request: IngredientRequest, db: Session = Depends(get_db)):
    try:
        logger.info(f"Received request to process ingredient: {request.name}")
        
        # Check if we already have this ingredient in the database
        repo = IngredientRepository(db)
        db_ingredient = repo.get_ingredient_by_name(request.name)
        
        if db_ingredient:
            logger.info(f"Found existing ingredient in database: {request.name}")
            # Convert DB model to Pydantic model
            # (This would need a function to correctly map the data)
            return ingredient_db_to_pydantic(db_ingredient)
        
        # If not in database, get from agent
        ingredient_finder = IngredientInfoAgentLangGraph()
        result = ingredient_finder.process_ingredient(request.name)
        
        # Save to database
        repo.create_ingredient(result)
        logger.info(f"Saved new ingredient to database: {request.name}")
        
        return result
    except Exception as e:
        logger.error(f"Error processing ingredient: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# @router.post("/process_ingredients")
# def process_ingredients_endpoint(ingredients: List[str], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
#     log_info("process_ingredients_endpoint called")
#     print(ingredients)
#     try:
#         # result = process_ingredients(db, ingredients, current_user.id)
#         result = None
#         log_info("process_ingredients_endpoint completed successfully")
#         return result
#     except Exception as e:
#         log_error(f"Error in process_ingredients_endpoint: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))
