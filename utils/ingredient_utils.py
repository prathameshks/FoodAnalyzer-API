import asyncio
import os
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.repositories import IngredientRepository
from interfaces.ingredientModels import IngredientAnalysisResult
from logger_manager import log_error, log_info
from services.ingredientFinderAgent import IngredientInfoAgentLangGraph
from langsmith import traceable
import pytz

from utils.db_utils import ingredient_db_to_pydantic

# Load environment variables
from env import PARALLEL_RATE_LIMIT


# Create a semaphore to limit concurrent API calls
llm_semaphore = asyncio.Semaphore(PARALLEL_RATE_LIMIT)


@traceable
async def process_single_ingredient(ingredient_name: str) -> IngredientAnalysisResult:
    """Process a single ingredient asynchronously with rate limiting"""
    try:
        # First check if ingredient exists in the database
        with SessionLocal() as db:
            repo = IngredientRepository(db)
            db_ingredient = repo.get_ingredient_by_name(ingredient_name)
            
            if db_ingredient:
                log_info(f"Using cached ingredient data for: {ingredient_name}")
                return ingredient_db_to_pydantic(db_ingredient)
        
        # If not in database, process it
        log_info(f"Processing new ingredient: {ingredient_name}")
        ingredient_finder = IngredientInfoAgentLangGraph()
        
        try:
            result = await ingredient_finder.process_ingredient_async(ingredient_name)
        except RuntimeError:
            result = ingredient_finder.process_ingredient(ingredient_name)
        
        # Important: Add an id field even for new ingredients
        # You can use a temporary id (will be replaced when saved to DB)
        result.id = 0  # Temporary ID
        
        # Save to database for future use
        with SessionLocal() as db:
            repo = IngredientRepository(db)
            db_ingredient = repo.create_ingredient(result)
            # Update with the real database ID
            result.id = db_ingredient.id
            
        return result
    except Exception as e:
        log_error(f"Error processing ingredient {ingredient_name}: {e}", e)
        # Return a minimal valid result for failed ingredients
        return IngredientAnalysisResult(
            name=ingredient_name,
            is_found=False,
            id=0,  # Add this missing required field
            alternate_names=[],
            safety_rating=0,
            description="Error processing this ingredient",
            health_effects=["Unknown"],
            details_with_source=[]
        )