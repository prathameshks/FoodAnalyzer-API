from sqlalchemy.orm import Session
from db.models import Ingredient
from fastapi import HTTPException
from cachetools import cached, TTLCache
from typing import List, Dict, Any
import requests

cache = TTLCache(maxsize=100, ttl=300)

class IngredientService:
    def __init__(self, db: Session):
        self.db = db

    def get_ingredient_by_name(self, name: str) -> Ingredient:
        return self.db.query(Ingredient).filter(Ingredient.name == name).first()

    @cached(cache)
    def fetch_ingredient_data_from_api(self, name: str) -> Dict[str, Any]:
        url = f"https://api.example.com/ingredients/{name}"
        response = requests.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch data for ingredient {name}")
        data = response.json()
        return {
            "nutritional_info": data.get("nutritional_info", {}),
            "description": data.get("description", ""),
            "origin": data.get("origin", ""),
            "allergens": data.get("allergens", ""),
            "vegan": data.get("vegan", False),
            "vegetarian": data.get("vegetarian", False)
        }

    def get_ingredient_data(self, name: str) -> Dict[str, Any]:
        ingredient = self.get_ingredient_by_name(name)
        if ingredient:
            return {
                "nutritional_info": ingredient.nutritional_info,
                "description": ingredient.description,
                "origin": ingredient.origin,
                "allergens": ingredient.allergens,
                "vegan": ingredient.vegan,
                "vegetarian": ingredient.vegetarian
            }
        data = self.fetch_ingredient_data_from_api(name)
        self.save_ingredient_data(name, data)
        return data

    def save_ingredient_data(self, name: str, data: Dict[str, Any]):
        ingredient = Ingredient(
            name=name,
            nutritional_info=data.get("nutritional_info", {}),
            description=data.get("description", ""),
            origin=data.get("origin", ""),
            allergens=data.get("allergens", ""),
            vegan=data.get("vegan", False),
            vegetarian=data.get("vegetarian", False)
        )
        self.db.add(ingredient)
        self.db.commit()
        self.db.refresh(ingredient)
