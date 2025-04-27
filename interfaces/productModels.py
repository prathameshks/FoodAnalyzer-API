from typing import List, Dict
from pydantic import BaseModel
from datetime import datetime

# Add this class to define the request body structure
class ProductIngredientsRequest(BaseModel):
    ingredients: List[str]

class ProductCreate(BaseModel):
    product_name: str
    ingredients: List[str]
    overall_safety_score: int
    suitable_diet_types: str
    allergy_warnings: List[str]
    usage_recommendations: str
    health_insights: Dict[str, List[str]]
    ingredient_interactions: List[str]
    key_takeaway: str
    ingredients_count: int
    user_id: int
    timestamp: datetime
    ingredient_ids: List[int]


