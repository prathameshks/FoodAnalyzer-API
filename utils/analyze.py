import asyncio
from datetime import datetime
import pytz
from typing import List, Dict, Any
from logger_manager import log_info, log_error
from services.productAnalyzerAgent import analyze_product_ingredients
from utils.ingredient_utils import process_single_ingredient

# Load environment variables
from env import PARALLEL_RATE_LIMIT

log_info(f"Using parallel rate limit of {PARALLEL_RATE_LIMIT}")

# Create a semaphore to limit concurrent API calls
llm_semaphore = asyncio.Semaphore(PARALLEL_RATE_LIMIT)


async def process_product_ingredients(product_ingredients: List[str]) -> Dict[str, Any]:    
    log_info(f"process_product_ingredients called for {len(product_ingredients)} ingredients")
    try:
        # Step 1: Process individual ingredients
        ingredient_results = []
            
        log_info(f"Starting parallel ingredient processing with rate limit {PARALLEL_RATE_LIMIT}")
        
        # Create tasks for parallel processing
        tasks = []
        for ingredient_name in product_ingredients:
            task = process_single_ingredient(ingredient_name)
            tasks.append(task)
        
        # Execute tasks concurrently with rate limiting
        ingredient_results = await asyncio.gather(*tasks)
        log_info(f"Completed parallel processing of {len(ingredient_results)} ingredients")
            
        product_analysis = await analyze_product_ingredients(
            ingredients_data=ingredient_results
        )
        
        # print("Product analysis result:", product_analysis)
        
        # Step 3: Prepare final response
        result = {
            "ingredients_count": len(product_ingredients),
            "processed_ingredients": ingredient_results,
            "ingredient_ids": product_analysis["ingredient_ids"],
            "overall_analysis": product_analysis,
            "timestamp": datetime.now(tz=pytz.timezone('Asia/Kolkata')).isoformat()
        }

        log_info("process_product_ingredients completed successfully")
        return result
        
    except Exception as e:
        log_error(f"Error in process_product_ingredients: {str(e)}",e)
        return None
