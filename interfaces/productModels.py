from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
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

class BasicProductInfo(BaseModel):
    product_id: str
    product_name: str
    brand: Optional[str] = ""
    category: Optional[str] = ""
    image_url: Optional[str] = None
    barcode: Optional[str] = None

class SafetyInfo(BaseModel):
    safety_score: float = 0
    is_safe: bool = False
    warnings: List[str] = []
    benefits: List[str] = []

class IngredientInfo(BaseModel):
    ingredients_list: List[str] = []
    ingredients_analysis: List[Dict[str, Any]] = []
    ingredient_count: int = 0

class AllergenInfo(BaseModel):
    allergens: List[str] = []
    has_allergens: bool = False

class DietaryInfo(BaseModel):
    dietary_flags: List[str] = []
    is_vegetarian: bool = False
    is_vegan: bool = False

class ProductAnalysisResponse(BaseModel):
    """Response model for product analysis by marker ID"""
    found: bool = Field(..., description="Whether the product was found")
    basic_info: BasicProductInfo = Field(..., description="Basic product information")
    safety_info: SafetyInfo = Field(..., description="Safety information about the product")
    ingredient_info: IngredientInfo = Field(..., description="Information about ingredients")
    allergen_info: AllergenInfo = Field(..., description="Information about allergens")
    dietary_info: DietaryInfo = Field(..., description="Dietary information")
    timestamp: str = Field(..., description="Timestamp of the response")


