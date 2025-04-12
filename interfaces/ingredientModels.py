from typing import Dict, List, Any, Optional, TypedDict
from pydantic import BaseModel, Field


# Define a structured output model
class IngredientAnalysisResult(BaseModel):
    name: str
    alternate_names: List[str] = Field(default_factory=list)
    is_found: bool = False
    safety_rating: int = 5
    description: str = "No information found."
    health_effects: List[str] = Field(default_factory=lambda: ["Unknown"])
    allergic_info: Optional[List[str]] = None  # New field
    diet_type: Optional[str] = None  # New field
    details_with_source: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        from_attributes = True  # Enable ORM mode

# Define typed state for LangGraph
class IngredientState(TypedDict):
    ingredient: str
    sources_data: List[Dict[str, Any]]
    status: str
    result: Optional[Dict[str, Any]]
    local_db_checked: bool
    web_search_done: bool
    wikipedia_checked: bool
    open_food_facts_checked: bool
    usda_checked: bool
    pubchem_checked: bool
    analysis_done: bool

class IngredientRequest(BaseModel):
    name: str
