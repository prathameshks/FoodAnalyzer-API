import asyncio
import os
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.repositories import IngredientRepository
from interfaces.ingredientModels import IngredientAnalysisResult
from services.ingredientFinderAgent import IngredientInfoAgentLangGraph
from dotenv import load_dotenv
from langsmith import traceable
import pytz

# Load environment variables
load_dotenv()

# Get rate limit from environment variable or use default
PARALLEL_RATE_LIMIT = int(os.getenv("PARALLEL_RATE_LIMIT", 10))

# Create a semaphore to limit concurrent API calls
llm_semaphore = asyncio.Semaphore(PARALLEL_RATE_LIMIT)


@traceable
async def process_single_ingredient(ingredient_name: str):
    """Process a single ingredient asynchronously with rate limiting"""
    # Create a new DB session for this specific task to avoid conflicts
    session = SessionLocal()

    try:
        # Check if ingredient exists in database
        repo = IngredientRepository(session)
        db_ingredient = repo.get_ingredient_by_name(ingredient_name)

        if db_ingredient:
            # Assuming ingredient_db_to_pydantic is now in a utils file, e.g., utils.db_utils
            from .db_utils import ingredient_db_to_pydantic
            ingredient_data = ingredient_db_to_pydantic(db_ingredient)
            return ingredient_data
        else:
            # Apply rate limiting for LLM calls only if not in database
            async with llm_semaphore:
                # Get from agent if not in database
                ingredient_finder = IngredientInfoAgentLangGraph()

                ingredient_data = await ingredient_finder.process_ingredient_async(ingredient_name)

                # Save to database for future use
                repo.create_ingredient(ingredient_data)

                return ingredient_data
    except Exception as e:
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