from sqlalchemy.orm import Session
from fastapi import HTTPException
from utils.fetch_data import fetch_product_data_from_api
from utils.file_operations import save_json_file
from models.ingredient import Ingredient
from models.product import Product
from services.ingredients import get_ingredient_by_name, save_ingredient_data, fetch_ingredient_data_from_api
from typing import Dict, Any
import json
from transformers import pipeline
from langchain import LangChain

def preprocess_data(barcode: str) -> Dict[str, Any]:
    data = fetch_product_data_from_api(barcode)
    product = data.get('product', {})

    product_info = {
        "product_name": product.get('product_name_en', product.get('product_name', 'N/A')),
        "generic_name": product.get('generic_name_en', product.get('generic_name', 'N/A')),
        "brands": product.get('brands', 'N/A'),
        "ingredients": [],
        "ingredients_text": product.get('ingredients_text_en', product.get('ingredients_text', 'N/A')),
        "ingredients_analysis": product.get('ingredients_analysis', {}),
        "nutriscore": product.get('nutriscore', {}),
        "nutrient_levels": product.get('nutrient_levels', {}),
        "nutriments": product.get('nutriments', {}),
        "data_quality_warnings": product.get('data_quality_warnings_tags', [])
    }

    ingredients_list = product.get('ingredients', [])
    for ingredient in ingredients_list:
        ingredient_info = {
            "text": ingredient.get('text', 'N/A'),
            "percent": ingredient.get('percent', ingredient.get('percent_estimate', 'N/A')),
            "vegan": ingredient.get('vegan', 'N/A'),
            "vegetarian": ingredient.get('vegetarian', 'N/A'),
            "sub_ingredients": []
        }
        sub_ingredients = ingredient.get('ingredients', [])
        for sub_ingredient in sub_ingredients:
            sub_ingredient_info = {
                "text": sub_ingredient.get('text', 'N/A'),
                "percent": sub_ingredient.get('percent', sub_ingredient.get('percent_estimate', 'N/A')),
                "vegan": sub_ingredient.get('vegan', 'N/A'),
                "vegetarian": sub_ingredient.get('vegetarian', 'N/A')
            }
            ingredient_info["sub_ingredients"].append(sub_ingredient_info)
        product_info["ingredients"].append(ingredient_info)

    return product_info

def validate_data(data: Dict[str, Any]) -> bool:
    required_fields = ["product_name", "generic_name", "brands", "ingredients", "nutriscore", "nutrient_levels", "nutriments"]
    for field in required_fields:
        if field not in data or not data[field]:
            return False
    return True

def clean_data(data: Dict[str, Any]) -> Dict[str, Any]:
    for ingredient in data["ingredients"]:
        if "percent" in ingredient and ingredient["percent"] == "N/A":
            ingredient["percent"] = 0
        for sub_ingredient in ingredient["sub_ingredients"]:
            if "percent" in sub_ingredient and sub_ingredient["percent"] == "N/A":
                sub_ingredient["percent"] = 0
    return data

def standardize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    for ingredient in data["ingredients"]:
        ingredient["text"] = ingredient["text"].lower()
        for sub_ingredient in ingredient["sub_ingredients"]:
            sub_ingredient["text"] = sub_ingredient["text"].lower()
    return data

def enrich_data(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    for ingredient in data["ingredients"]:
        ingredient_data = get_ingredient_by_name(db, ingredient["text"])
        if not ingredient_data:
            ingredient_data = fetch_ingredient_data_from_api(ingredient["text"])
            save_ingredient_data(db, ingredient["text"], ingredient_data)
        ingredient["nutritional_info"] = ingredient_data
    return data

def process_data(db: Session, barcode: str) -> Dict[str, Any]:
    data = preprocess_data(barcode)
    if not validate_data(data):
        raise HTTPException(status_code=400, detail="Invalid data")
    data = clean_data(data)
    data = standardize_data(data)
    data = enrich_data(db, data)
    
    # Save product details in the Product model
    product = Product(
        product_name=data["product_name"],
        generic_name=data["generic_name"],
        brands=data["brands"],
        ingredients=data["ingredients"],
        ingredients_text=data["ingredients_text"],
        ingredients_analysis=data["ingredients_analysis"],
        nutriscore=data["nutriscore"],
        nutrient_levels=data["nutrient_levels"],
        nutriments=data["nutriments"],
        data_quality_warnings=data["data_quality_warnings"]
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Save ingredient details in the Ingredient model
    for ingredient in data["ingredients"]:
        ingredient_data = get_ingredient_by_name(db, ingredient["text"])
        if not ingredient_data:
            ingredient_data = fetch_ingredient_data_from_api(ingredient["text"])
            save_ingredient_data(db, ingredient["text"], ingredient_data)
        ingredient["nutritional_info"] = ingredient_data
    
    save_json_file(barcode, data)
    return data

def integrate_hugging_face_transformers(model_name: str, text: str) -> str:
    nlp = pipeline("fill-mask", model=model_name)
    result = nlp(text)
    return result[0]['sequence']

def process_ingredients(db: Session, ingredients: list[str], user_id: int) -> dict[str, Any]:
    # First agent: Correct mistakes in the ingredient list using NLP, check the database for details, and search the web if not found
    corrected_ingredients = []
    for ingredient in ingredients:
        corrected_ingredient = integrate_hugging_face_transformers("bert-base-uncased", ingredient)
        ingredient_data = get_ingredient_by_name(db, corrected_ingredient)
        if not ingredient_data:
            ingredient_data = fetch_ingredient_data_from_api(corrected_ingredient)
            save_ingredient_data(db, corrected_ingredient, ingredient_data)
        corrected_ingredients.append({
            "name": corrected_ingredient,
            "pros_cons": ingredient_data
        })

    # Second agent: Analyze the ingredient list and return data including safety, score, eating limit, and key insights
    analysis_results = []
    for ingredient in corrected_ingredients:
        safety_score = LangChain.analyze_safety(ingredient["name"])
        score = LangChain.analyze_score(ingredient["name"])
        eating_limit = LangChain.analyze_eating_limit(ingredient["name"])
        key_insights = LangChain.analyze_key_insights(ingredient["name"])
        analysis_results.append({
            "ingredient": ingredient["name"],
            "safety": safety_score,
            "score": score,
            "eating_limit": eating_limit,
            "key_insights": key_insights
        })

    # Save the results in user search history and product
    for result in analysis_results:
        product = Product(
            product_name=result["ingredient"],
            ingredients=[result],
            ingredients_analysis=result,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

    return {
        "corrected_ingredients": corrected_ingredients,
        "analysis_results": analysis_results
    }
