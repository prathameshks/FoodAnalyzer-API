import os
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
from langchain_community.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from services.logging_service import log_info, log_error
from dotenv import load_dotenv

load_dotenv()


def preprocess_data(barcode: str) -> Dict[str, Any]:
    log_info("preprocess_data function called")
    try:
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

        log_info("preprocess_data function completed successfully")
        return product_info
    except Exception as e:
        log_error(f"Error in preprocess_data function: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def validate_data(data: Dict[str, Any]) -> bool:
    log_info("validate_data function called")
    try:
        required_fields = ["product_name", "generic_name", "brands", "ingredients", "nutriscore", "nutrient_levels", "nutriments"]
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        log_info("validate_data function completed successfully")
        return True
    except Exception as e:
        log_error(f"Error in validate_data function: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def clean_data(data: Dict[str, Any]) -> Dict[str, Any]:
    log_info("clean_data function called")
    try:
        for ingredient in data["ingredients"]:
            if "percent" in ingredient and ingredient["percent"] == "N/A":
                ingredient["percent"] = 0
            for sub_ingredient in ingredient["sub_ingredients"]:
                if "percent" in sub_ingredient and sub_ingredient["percent"] == "N/A":
                    sub_ingredient["percent"] = 0
        log_info("clean_data function completed successfully")
        return data
    except Exception as e:
        log_error(f"Error in clean_data function: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def standardize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    log_info("standardize_data function called")
    try:
        for ingredient in data["ingredients"]:
            ingredient["text"] = ingredient["text"].lower()
            for sub_ingredient in ingredient["sub_ingredients"]:
                sub_ingredient["text"] = sub_ingredient["text"].lower()
        log_info("standardize_data function completed successfully")
        return data
    except Exception as e:
        log_error(f"Error in standardize_data function: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def enrich_data(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    log_info("enrich_data function called")
    try:
        for ingredient in data["ingredients"]:
            ingredient_data = get_ingredient_by_name(db, ingredient["text"])
            if not ingredient_data:
                ingredient_data = fetch_ingredient_data_from_api(ingredient["text"])
                save_ingredient_data(db, ingredient["text"], ingredient_data)
            ingredient["nutritional_info"] = ingredient_data

            # Additional API calls for ingredient safety analysis, nutritional information, score analysis, origin and source, and allergen information
            # ingredient["safety_info"] = fetch_ingredient_safety_info(ingredient["text"])
            # ingredient["nutritional_info"] = fetch_ingredient_nutritional_info(ingredient["text"])
            # ingredient["score_info"] = fetch_ingredient_score_info(ingredient["text"])
            # ingredient["origin_info"] = fetch_ingredient_origin_info(ingredient["text"])
            # ingredient["allergen_info"] = fetch_ingredient_allergen_info(ingredient["text"])

        log_info("enrich_data function completed successfully")
        return data
    except Exception as e:
        log_error(f"Error in enrich_data function: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def process_data(db: Session, barcode: str) -> Dict[str, Any]:
    log_info("process_data function called")
    try:
        data = preprocess_data(barcode)
        if not validate_data(data):
            log_error("Invalid data in process_data function")
            raise HTTPException(status_code=400, detail="Invalid data")
        data = clean_data(data)
        data = standardize_data(data)
        # data = enrich_data(db, data)
        
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

            # LangChain method calls for ingredient analysis
            ingredient["safety"] = LangChain.analyze_safety(ingredient["text"])
            ingredient["score"] = LangChain.analyze_score(ingredient["text"])
            ingredient["eating_limit"] = LangChain.analyze_eating_limit(ingredient["text"])
            ingredient["key_insights"] = LangChain.analyze_key_insights(ingredient["text"])
        
        save_json_file(barcode, data)
        log_info("process_data function completed successfully")
        return data
    except Exception as e:
        log_error(f"Error in process_data function: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def integrate_hugging_face_transformers(model_name: str, text: str) -> str:
    log_info("integrate_hugging_face_transformers function called")
    try:
        nlp = pipeline("fill-mask", model=model_name)
        result = nlp(text)
        log_info("integrate_hugging_face_transformers function completed successfully")
        return result[0]['sequence']
    except Exception as e:
        log_error(f"Error in integrate_hugging_face_transformers function: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def process_ingredients(db: Session, ingredients: list[str], user_id: int) -> dict[str, Any]:
    log_info("process_ingredients function called")
    try:
        # Initialize LangChain components
        llm = OpenAI(temperature=0.7,
                     openai_api_key=os.getenv("OPENAI_API_KEY"))
        
        # Create prompt templates for different analyses
        safety_template = PromptTemplate(
            input_variables=["ingredient"],
            template="Analyze the safety of {ingredient} as a food ingredient."
        )
        
        score_template = PromptTemplate(
            input_variables=["ingredient"],
            template="Rate {ingredient} on a scale of 1-10 for nutritional value."
        )
        
        # Create chains
        safety_chain = LLMChain(llm=llm, prompt=safety_template)
        score_chain = LLMChain(llm=llm, prompt=score_template)
        
        analysis_results = []
        for ingredient in ingredients:
            safety = safety_chain.run(ingredient=ingredient)
            score = score_chain.run(ingredient=ingredient)
            
            analysis_results.append({
                "ingredient": ingredient,
                "safety_analysis": safety,
                "nutritional_score": score
            })
        
        log_info("process_ingredients completed successfully")
        return {"results": analysis_results}
        
    except Exception as e:
        log_error(f"Error in process_ingredients: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing ingredients")