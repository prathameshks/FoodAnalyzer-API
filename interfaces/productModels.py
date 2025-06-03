from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime

# Add this class to define the request body structure
class ProductIngredientsRequest(BaseModel):
    ingredients: List[str]

class ProductCreate(BaseModel):
    product_name: str
    ingredients: List[str]|str
    overall_safety_score: int
    suitable_diet_types: str
    allergy_warnings: List[str]|str
    usage_recommendations: str
    health_insights: Dict[str, List[str]]|str
    ingredient_interactions: List[str]|str
    key_takeaway: str
    ingredients_count: int
    user_id: int
    timestamp: datetime
    ingredient_ids: List[int]|str

class SafetyScore(BaseModel):
    isPresent: bool
    value: Optional[int] = None

class ProductInfo(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    brand: Optional[str] = None
    manufacturing_places: Optional[str] = None
    stores: Optional[str] = None
    countries: Optional[str] = None

class IngredientInfo(BaseModel):
    ingredients_text: Optional[str] = None
    ingredients_analysis: Optional[List[Dict[str, Any]]] = None # Adjust type if analysis has a specific structure
    additives: Optional[List[str]] = None

class AllergenInfo(BaseModel):
    allergens: Optional[List[str]] = None
    traces: Optional[List[str]] = None

class DietInfo(BaseModel):
    vegan: Optional[bool] = None
    vegetarian: Optional[bool] = None

class ProductAnalysisResponse(BaseModel):
    found: bool
    safety_score: SafetyScore
    product_info: Optional[ProductInfo] = None
    ingredient_info: Optional[IngredientInfo] = None
    allergen_info: Optional[AllergenInfo] = None
    diet_info: Optional[DietInfo] = None
    nutritional_info: Optional[Dict[str, Any]] = None # Adjust type if nutritional info has a specific structure
    manufacturing_info: Optional[Dict[str, Any]] = None # Adjust type if manufacturing info has a specific structure


