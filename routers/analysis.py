import asyncio
import os
from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
import pytz
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from db.models import User, Ingredient
from interfaces.ingredientModels import IngredientAnalysisResult, IngredientRequest
from interfaces.productModels import ProductIngredientsRequest
from logger_manager import log_info, log_error
from db.database import get_db,SessionLocal
from db.repositories import IngredientRepository
from dotenv import load_dotenv
from langsmith import traceable
from services.ingredientFinderAgent import IngredientInfoAgentLangGraph
from services.productAnalyzerAgent import analyze_product_ingredients
from utils.db_utils import ingredient_db_to_pydantic
from services.analysis_service import get_product_data_by_marker_id as get_analysis_service_data
from utils.ingredient_utils import process_single_ingredient

# Load environment variables
load_dotenv()

# Get rate limit from environment variable or use default
PARALLEL_RATE_LIMIT = int(os.getenv("PARALLEL_RATE_LIMIT", 10))
log_info(f"Using parallel rate limit of {PARALLEL_RATE_LIMIT}")

# Create a semaphore to limit concurrent API calls
llm_semaphore = asyncio.Semaphore(PARALLEL_RATE_LIMIT)


router = APIRouter()


# process single ingredient 
@router.post("/process_ingredient", response_model=IngredientAnalysisResult)
@traceable
async def process_ingredient_endpoint(request: IngredientRequest, db: Session = Depends(get_db)):
    try:
        log_info(f"Received request to process ingredient: {request.name}")
        
        # Check if we already have this ingredient in the database
        repo = IngredientRepository(db)
        db_ingredient = repo.get_ingredient_by_name(request.name)
        
        if db_ingredient:
            log_info(f"Found existing ingredient in database: {request.name}")
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
        log_info(f"Saved new ingredient to database: {request.name}")
        
        return result
    except Exception as e:
        log_error(f"Error processing ingredient: {e}",e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
        
        # Safely get user preferences, handling the case where the preferences table doesn't exist
        user_preferences = {}
        if current_user:
            user_preferences["user_id"] = current_user.id
            try:
                # Only try to access preferences if the relationship exists
                if hasattr(current_user, 'preferences') and current_user.preferences:
                    user_preferences["allergies"] = current_user.preferences[0].allergens
                    user_preferences["dietary_restrictions"] = current_user.preferences[0].dietary_restrictions
                else:
                    user_preferences["allergies"] = None
                    user_preferences["dietary_restrictions"] = None
            except Exception as e:
                log_error(f"Error accessing user preferences: {e}", e)
                user_preferences["allergies"] = None
                user_preferences["dietary_restrictions"] = None
        
        product_analysis = await analyze_product_ingredients(
            ingredients_data=ingredient_results,
            user_preferences=user_preferences
        )
        
        # print("Product analysis result:", product_analysis)
         
        # Step 3: Prepare final response
        result = {
            "ingredients_count": len(ingredients),
            "processed_ingredients": ingredient_results,
            "ingredient_ids": product_analysis["ingredient_ids"],
            "overall_analysis": product_analysis,
            "user_id": current_user.id if current_user else None,
            "timestamp": datetime.now(tz=pytz.timezone('Asia/Kolkata')).isoformat()
        }
        
        log_info("process_ingredients_endpoint completed successfully")
        return result
        
    except Exception as e:
        log_error(f"Error in process_ingredients_endpoint: {str(e)}",e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/get_by_marker_id/{target_id}", response_model=ProductAnalysisResponse)
async def get_analysis_by_marker_id(target_id: str, db: Session = Depends(get_db)):
    """
    Retrieves product analysis and ingredient information by marker ID.
    """
    log_info(f"Received request for analysis by marker ID: {target_id}")
    try:
        product_data = get_analysis_service_data(db, target_id)

        if not product_data:
            raise HTTPException(status_code=404, detail=f"Product not found for marker ID: {target_id}")

        log_info(f"Successfully retrieved product data for marker ID: {target_id}")
        return product_data

    except Exception as e:
        log_error(f"Error in get_analysis_by_marker_id: {str(e)}", e) 
        raise HTTPException(status_code=500, detail="Internal Server Error")
