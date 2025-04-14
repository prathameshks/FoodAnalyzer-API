import asyncio
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import pytz
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from db.models import User
from interfaces.ingredientModels import IngredientAnalysisResult, IngredientRequest
from interfaces.productModels import ProductIngredientsRequest
from services.auth_service import get_current_user
from logger_manager import log_info, log_error,logger
from db.database import get_db,SessionLocal
from db.repositories import IngredientRepository
from dotenv import load_dotenv
from langsmith import traceable

from services.ingredientFinderAgent import IngredientInfoAgentLangGraph
from services.productAnalyzerAgent import analyze_product_ingredients

# Load environment variables
load_dotenv()

# Get rate limit from environment variable or use default
PARALLEL_RATE_LIMIT = int(os.getenv("PARALLEL_RATE_LIMIT", 10))
log_info(f"Using parallel rate limit of {PARALLEL_RATE_LIMIT}")

# Create a semaphore to limit concurrent API calls
llm_semaphore = asyncio.Semaphore(PARALLEL_RATE_LIMIT)

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
@traceable
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
        # run async function if found event loop already running use normal function 
        try:
            result = await ingredient_finder.process_ingredient_async(request.name)
        except RuntimeError:
            # If the event loop is not running, run the function normally
            result = ingredient_finder.process_ingredient(request.name)
                    
        
        # Save to database
        repo.create_ingredient(result)
        logger.info(f"Saved new ingredient to database: {request.name}")
        
        return result
    except Exception as e:
        logger.error(f"Error processing ingredient: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

async def process_single_ingredient(ingredient_name: str):
    """Process a single ingredient asynchronously with rate limiting"""
    log_info(f"Starting processing for ingredient (async): {ingredient_name}")
    
    # Create a new DB session for this specific task to avoid conflicts
    session = SessionLocal()
    
    try:
        # Check if ingredient exists in database
        repo = IngredientRepository(session)
        db_ingredient = repo.get_ingredient_by_name(ingredient_name)
        
        if db_ingredient:
            log_info(f"Found existing ingredient in database: {ingredient_name}")
            ingredient_data = ingredient_db_to_pydantic(db_ingredient)
            return ingredient_data
        else:
            # Apply rate limiting for LLM calls only if not in database
            async with llm_semaphore:
                log_info(f"Acquired semaphore for: {ingredient_name}")
                # Get from agent if not in database
                log_info(f"Fetching ingredient from agent: {ingredient_name}")
                # Create a new instance for thread safety
                ingredient_finder = IngredientInfoAgentLangGraph()
                
                # FIXED: Use the async version directly instead of the sync wrapper
                ingredient_data = await ingredient_finder.process_ingredient_async(ingredient_name)
                
                # Save to database for future use
                repo.create_ingredient(ingredient_data)
                log_info(f"Saved new ingredient to database: {ingredient_name}")
                
                return ingredient_data
    except Exception as e:
        log_error(f"Error processing ingredient {ingredient_name}: {str(e)}")
        # Return a minimal result on error to avoid failing the entire batch
        return IngredientAnalysisResult(
            name=ingredient_name,
            is_found=False,
            safety_rating=0,
            description=f"Error during processing: {str(e)}",
            health_effects=["Error during processing"],
            allergic_info=[],
            diet_type="unknown",
            details_with_source=[]
        )
    finally:
        # Important: Close the session when done
        session.close()

@router.post("/process_product_ingredients", response_model=Dict[str, Any])
@traceable
async def process_ingredients_endpoint(product_ingredient: ProductIngredientsRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log_info(f"process_ingredients_endpoint called for {len(product_ingredient.ingredients)} ingredients")
    ingredients = product_ingredient.ingredients
    try:
        # Step 1: Process individual ingredients
        ingredient_results = []
            
        log_info(f"Starting parallel ingredient processing with rate limit {PARALLEL_RATE_LIMIT}")
        
        # Create tasks for parallel processing
        tasks = []
        for ingredient_name in ingredients:
            task = process_single_ingredient(ingredient_name)
            tasks.append(task)
        
        # Execute tasks concurrently with rate limiting
        ingredient_results = await asyncio.gather(*tasks)
        log_info(f"Completed parallel processing of {len(ingredient_results)} ingredients")
                
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
            "timestamp": datetime.now(tz=pytz.timezone('Asia/Kolkata')).isoformat()
        }
        
        log_info("process_ingredients_endpoint completed successfully")
        return result
        
    except Exception as e:
        log_error(f"Error in process_ingredients_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")