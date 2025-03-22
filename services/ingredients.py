from sqlalchemy.orm import Session
from models.ingredient import Ingredient
from fastapi import HTTPException
from cachetools import cached, TTLCache
from typing import List, Dict, Any
import requests
from utils.fetch_data import fetch_ingredient_data_from_api

cache = TTLCache(maxsize=100, ttl=300)

def get_ingredient_by_name(db: Session, name: str) -> Ingredient:
    return db.query(Ingredient).filter(Ingredient.name == name).first()

@cached(cache)
def fetch_ingredient_data_from_api(name: str) -> Dict[str, Any]:
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

def get_ingredient_data(db: Session, name: str) -> Dict[str, Any]:
    ingredient = get_ingredient_by_name(db, name)
    if ingredient:
        return {
            "nutritional_info": ingredient.nutritional_info,
            "description": ingredient.description,
            "origin": ingredient.origin,
            "allergens": ingredient.allergens,
            "vegan": ingredient.vegan,
            "vegetarian": ingredient.vegetarian
        }
    data = fetch_ingredient_data_from_api(name)
    save_ingredient_data(db, name, data)
    return data

def save_ingredient_data(db: Session, name: str, data: Dict[str, Any]):
    ingredient = Ingredient(
        name=name,
        nutritional_info=data.get("nutritional_info", {}),
        description=data.get("description", ""),
        origin=data.get("origin", ""),
        allergens=data.get("allergens", ""),
        vegan=data.get("vegan", False),
        vegetarian=data.get("vegetarian", False)
    )
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)

def filter_ingredients_by_preferences(ingredients: List[Dict[str, Any]], preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
    filtered_ingredients = []
    for ingredient in ingredients:
        if preferences.get("low_sugar") and ingredient.get("sugar", 0) > 5:
            continue
        if preferences.get("low_fat") and ingredient.get("fat", 0) > 5:
            continue
        if preferences.get("allergens") and any(allergen in ingredient.get("allergens", []) for allergen in preferences["allergens"]):
            continue
        filtered_ingredients.append(ingredient)
    return filtered_ingredients
