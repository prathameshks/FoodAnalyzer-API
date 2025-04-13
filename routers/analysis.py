from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from db.models import User
from interfaces.ingredientModels import IngredientAnalysisResult, IngredientRequest
from interfaces.productModels import ProductIngredientsRequest
from services.auth_service import get_current_user
from logger_manager import log_info, log_error,logger
from db.database import get_db
from db.repositories import IngredientRepository

from services.ingredientFinderAgent import IngredientInfoAgentLangGraph
from services.productAnalyzerAgent import analyze_product_ingredients


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


@router.post("/process_product_ingredients", response_model=Dict[str, Any])
async def process_ingredients_endpoint(product_ingredient: ProductIngredientsRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log_info(f"process_ingredients_endpoint called for {len(product_ingredient.ingredients)} ingredients")
    ingredients = product_ingredient.ingredients
    try:
        # Step 1: Process individual ingredients
        ingredient_results = []
        ingredient_finder = IngredientInfoAgentLangGraph()
        repo = IngredientRepository(db)
        
        for ingredient_name in ingredients:
            log_info(f"Processing ingredient: {ingredient_name}")
            
            # Check if ingredient exists in database
            db_ingredient = repo.get_ingredient_by_name(ingredient_name)
            
            if db_ingredient:
                log_info(f"Found existing ingredient in database: {ingredient_name}")
                ingredient_data = ingredient_db_to_pydantic(db_ingredient)
            else:
                # Get from agent if not in database
                log_info(f"Fetching ingredient from agent: {ingredient_name}")
                ingredient_data = ingredient_finder.process_ingredient(ingredient_name)
                
                # Save to database for future use
                repo.create_ingredient(ingredient_data)
                log_info(f"Saved new ingredient to database: {ingredient_name}")
            
            ingredient_results.append(ingredient_data)
        
        # Step 2: Generate aggregate analysis with product analyzer agent
        
        product_analysis = await analyze_product_ingredients(
            ingredients_data=ingredient_results,
            user_preferences={
                "user_id": current_user.id,
                "allergies": current_user.preferences[0].allergens if current_user.preferences else None,
                "dietary_restrictions": current_user.preferences[0].dietary_restrictions if current_user.preferences else None
            } if current_user else {}
        )
        
        # Step 3: Prepare final response
        result = {
            "ingredients_count": len(ingredients),
            "processed_ingredients": ingredient_results,
            "overall_analysis": product_analysis,
            "user_id": current_user.id if current_user else None,
            "timestamp": datetime.now().isoformat()
        }
        
        log_info("process_ingredients_endpoint completed successfully")
        return result
        
    except Exception as e:
        log_error(f"Error in process_ingredients_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))