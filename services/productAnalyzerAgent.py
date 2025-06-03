import os
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from logger_manager import log_error, log_info
from interfaces.ingredientModels import IngredientAnalysisResult

# Load environment variables
from env import LLM_API_KEY, LLM_MODEL_NAME

async def analyze_product_ingredients(
    ingredients_data: List[IngredientAnalysisResult],
    user_preferences: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze multiple ingredients to provide a comprehensive product analysis
    for AR display, considering user preferences and dietary restrictions.
    """
    log_info(f"Analyzing product with {len(ingredients_data)} ingredients")
    
    # Initialize LLM    
    llm = ChatGoogleGenerativeAI(
        google_LLM_API_KEY=LLM_API_KEY,
        model=LLM_MODEL_NAME,
        temperature=0.2  # Lower temperature for more factual responses
    )
    
    # Prepare ingredient data for the prompt
    ingredients_summary = []
    ingredient_ids = []
    for i, ingredient in enumerate(ingredients_data):
        ingredient_info = f"""
Ingredient {i+1}: {ingredient.name}
Safety Rating: {ingredient.safety_rating}/10
Diet Type: {ingredient.diet_type if hasattr(ingredient, 'diet_type') else 'Unknown'}
Allergic Info: {', '.join(ingredient.allergic_info) if hasattr(ingredient, 'allergic_info') and ingredient.allergic_info else 'None known'}
Health Effects: {', '.join(ingredient.health_effects) if ingredient.health_effects else 'Unknown'}
Description: {ingredient.description[:200] + '...' if len(ingredient.description) > 200 else ingredient.description}
"""
        ingredients_summary.append(ingredient_info)
        ingredient_ids.append(ingredient.id)
    
    # Add user preferences context if available
    user_context = ""
    if user_preferences:
        allergies = user_preferences.get("allergies", "None specified")
        diet = user_preferences.get("dietary_restrictions", "None specified")
        user_context = f"""
## Also consider the following user preferences:
        
User has the following preferences:
- Dietary Restrictions: {diet}
- Allergies: {allergies}
"""
    
    # Create the analysis prompt
    analysis_prompt = f"""
# PRODUCT INGREDIENT ANALYSIS TASK

You are an expert food scientist and nutritionist analyzing a product's ingredients.
Based on the detailed information about each ingredient below, provide a comprehensive
analysis that would be helpful for a consumer viewing this in an AR application.

## INGREDIENTS INFORMATION:
{''.join(ingredients_summary)}

{user_context}

## REQUIRED ANALYSIS:
1. Overall Safety Score (1-10): Calculate this based on individual ingredient safety scores
2. Suitable Diet Types: Determine if this product is for vegan, vegetarian, or Non-Vegetarian
3. Allergy Warnings: Flag any potential allergens present related to food not more than 5 combine if needed
4. Usage Recommendations: Provide safe consumption limits or usage guidance
5. Health Insights: Summarize health benefits and concerns of the product not more than 3 for each and also focus on health not other aspects, may combine if needed but keep short
6. Ingredient Interactions: Note any ingredients that may interact when combined
7. Key Takeaway: A single sentence summarizing if this product is recommended

## FORMAT YOUR RESPONSE AS JSON:
{{
  "overall_safety_score": (number between 1-10),
  "suitable_diet_types": (strings from "Vegan", "Vegetarian", "Non-Vegetarian"),
  "allergy_warnings": (array of strings),
  "usage_recommendations": (string with specific guidance),
  "health_insights": {{
    "benefits": (array of strings),
    "concerns": (array of strings)
  }},
  "ingredient_interactions": (array of strings),
  "key_takeaway": (string)
}}

Only include factual information based on the provided data. If information is unavailable for any field, use appropriate default values. If the data required is too obvious then give appropriate answer.
IMPORTANT: Ensure your response is valid JSON with double quotes (") around property names and string values. 
Avoid single quotes (') for JSON properties and values.
Ensure all elements in arrays and objects are separated by commas, and don't include trailing commas.
Also strictly follow the JSON format in your response.

"""
    
    log_info("Sending product analysis prompt to LLM")
    
    try:
        # Process with LLM
        message = HumanMessage(content=analysis_prompt)
        llm_response = llm.invoke([message])
        analysis_text = llm_response.content
        
        # Extract JSON from response
        import json
        import re
        
        # Find JSON in the response using regex
        json_match = re.search(r'({.*})', analysis_text.replace('\n', ' '), re.DOTALL)
        
        if json_match:
            try:
                analysis = json.loads(json_match.group(0))
                analysis["ingredient_ids"] = ingredient_ids
                log_info("Successfully parsed product analysis")
                return analysis
            except json.JSONDecodeError as e:
                log_error(f"JSON parsing error: {e}",e)
                # Return a simplified analysis on error
                return {
                    "overall_safety_score": calculate_average_safety(ingredients_data),
                    "error": "Failed to parse complete analysis",
                    "ingredient_count": len(ingredients_data),
                    "key_takeaway": "Analysis error occurred, please check individual ingredients",
                    "ingredient_ids": ingredient_ids
                }
        else:
            log_error("Could not find JSON in LLM response")
            return {
                "overall_safety_score": calculate_average_safety(ingredients_data),
                "error": "Failed to generate structured analysis",
                "ingredient_count": len(ingredients_data),
                "ingredient_ids": ingredient_ids
            }
    
    except Exception as e:
        log_error(f"Error in product analysis: {e}",e)
        # Fallback analysis based on simple calculations
        return generate_fallback_analysis(ingredients_data, ingredient_ids)


def calculate_average_safety(ingredients_data: List[IngredientAnalysisResult]) -> float:
    """Calculate average safety score from ingredients."""
    safety_scores = [i.safety_rating for i in ingredients_data if i.safety_rating is not None]
    if not safety_scores:
        return 5.0  # Default middle value
    return round(sum(safety_scores) / len(safety_scores), 1)


def generate_fallback_analysis(ingredients_data: List[IngredientAnalysisResult], ingredient_ids: List[int]) -> Dict[str, Any]:
    """Generate a basic analysis when LLM processing fails."""
    # Extract known allergens
    allergens = []
    for ingredient in ingredients_data:
        if hasattr(ingredient, 'allergic_info') and ingredient.allergic_info:
            allergens.extend(ingredient.allergic_info)
    
    # Determine diet type based on ingredients
    diet_types = []
    all_vegan = all(getattr(i, 'diet_type', '') == 'vegan' for i in ingredients_data 
                    if hasattr(i, 'diet_type') and i.diet_type)
    all_vegetarian = all(getattr(i, 'diet_type', '') in ['vegan', 'vegetarian'] 
                         for i in ingredients_data if hasattr(i, 'diet_type') and i.diet_type)
    
    if all_vegan:
        diet_types.append("Vegan")
    if all_vegetarian:
        diet_types.append("Vegetarian")
    
    # Calculate safety score
    safety_score = calculate_average_safety(ingredients_data)
    
    return {
        "overall_safety_score": safety_score,
        "suitable_diet_types": diet_types,
        "allergy_warnings": list(set(allergens)),
        "usage_recommendations": "Please refer to product packaging for usage guidelines",
        "health_insights": {
            "benefits": [],
            "concerns": ["Analysis system encountered an error, please check individual ingredients"]
        },
        "key_takeaway": f"Product has {len(ingredients_data)} ingredients with average safety score of {safety_score}/10",
        "ingredient_ids": ingredient_ids
    }
