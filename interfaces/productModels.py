from typing import List
from pydantic import BaseModel

# Add this class to define the request body structure
class ProductIngredientsRequest(BaseModel):
    ingredients: List[str]
