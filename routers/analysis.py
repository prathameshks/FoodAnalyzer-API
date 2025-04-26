import asyncio
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
import pytz
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from db.models import User, Ingredient
from interfaces.ingredientModels import IngredientAnalysisResult, IngredientRequest
from interfaces.productModels import ProductIngredientsRequest,ProductData
from services.auth_service import get_current_user
from logger_manager import log_info, log_error, logger
from db.database import get_db,SessionLocal
from db.repositories import IngredientRepository, ProductRepository
from dotenv import load_dotenv
from langsmith import traceable
import io
from ultralytics import YOLO
from services.ingredientFinderAgent import IngredientInfoAgentLangGraph
from services.productAnalyzerAgent import analyze_product_ingredients

# Load environment variables
load_dotenv()

# Get rate limit from environment variable or use default
PARALLEL_RATE_LIMIT = int(os.getenv("PARALLEL_RATE_LIMIT", 10))
log_info(f"Using parallel rate limit of {PARALLEL_RATE_LIMIT}")

# Create a semaphore to limit concurrent API calls
llm_semaphore = asyncio.Semaphore(PARALLEL_RATE_LIMIT)

# Load YOLO model
yolo_model = YOLO("yolov8n-seg.pt")  # Downloaded automatically if needed
UPLOADED_IMAGES_DIR = "uploaded_images"
if not os.path.exists(UPLOADED_IMAGES_DIR):
    os.makedirs(UPLOADED_IMAGES_DIR)


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


def extract_product_from_image_yolo(image_path: str) -> str | None:
    """Extracts the product image using YOLOv8 with preprocessing and postprocessing."""
    try:
        # Load image
        image = cv2.imread(image_path)

        # Preprocessing: Resize image
        target_size = (640, 640)
        image_resized = cv2.resize(image, target_size)

        # Run inference with YOLO
        results = yolo_model(image_resized)

        if not results:
            print("No objects detected by YOLO.")
            return None

        # Process results
        result = results[0]
        masks = result.masks

        if masks is None:
            print("No segmentation masks found by YOLO.")
            return None

        # Select the largest mask
        largest_mask_index = np.argmax([mask.area for mask in masks])
        largest_mask_tensor = masks[largest_mask_index].data.cpu()
        largest_mask = largest_mask_tensor.numpy().astype(np.uint8)

        # Resize the mask to the original image size
        largest_mask = cv2.resize(largest_mask, (image.shape[1], image.shape[0]))

        # Postprocessing: Basic mask cleanup (dilation/erosion)
        kernel = np.ones((5, 5), np.uint8)
        mask_cleaned = cv2.dilate(largest_mask, kernel, iterations=1)
        mask_cleaned = cv2.erode(mask_cleaned, kernel, iterations=1)
        
        # Create a masked image
        masked_image = np.zeros_like(image)
        masked_image[mask_cleaned.astype(bool)] = image[mask_cleaned.astype(bool)]

        # Crop the image
        y_coords, x_coords = np.where(mask_cleaned)
        x_min, x_max = np.min(x_coords), np.max(x_coords)
        y_min, y_max = np.min(y_coords), np.max(y_coords)
        cropped_image = masked_image[y_min:y_max, x_min:x_max]        

        # Save the cropped image
        cropped_image_path = os.path.join(
            UPLOADED_IMAGES_DIR, f"{uuid.uuid4()}.jpg"
        )
        cropped_image_bgr = cv2.cvtColor(cropped_image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(cropped_image_path, cropped_image_bgr)

        return cropped_image_path
    except Exception as e:
        print(f"Error during image processing: {e}")
        return None


@router.post("/process_image")
async def process_image(image: UploadFile = File(...)):
    """
    Endpoint to process an image and extract the product using SAM.

    Args:
        image: The uploaded image file.

    Returns:
        JSON response with the path to the processed image or an error message.
    """
    try:
        # Save the uploaded image temporarily
        temp_image_filename = f"{uuid.uuid4()}.jpg"
        temp_image_path = os.path.join(UPLOADED_IMAGES_DIR, temp_image_filename)
        contents = await image.read()
        img = Image.open(io.BytesIO(contents))
        img.save(temp_image_path, "JPEG")

        print("Image saved temporarily to:", temp_image_path)

        # Extract the product
        extracted_product_path = extract_product_from_image_yolo(temp_image_path)

        # Remove the temporary file
        os.remove(temp_image_path)
        print("Removed temporary file")

        if extracted_product_path:
            print("Product extracted and saved to:", extracted_product_path)
            return JSONResponse(
                {
                    "message": "Product extracted successfully",
                    "product_image_path": extracted_product_path,
                    "image": FileResponse(extracted_product_path, media_type="image/jpeg")
                }
            )
        else:
            print("Failed to extract the product.")
            return JSONResponse(
                {"error": "Failed to extract product from image"}, status_code=500
            )

    except Exception as e:
        print("Error:", e)
        return JSONResponse({"error": str(e)}, status_code=500)


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
