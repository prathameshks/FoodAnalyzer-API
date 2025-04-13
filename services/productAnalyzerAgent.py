import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from logger_manager import logger
from interfaces.ingredientModels import IngredientAnalysisResult

# Load environment variables
load_dotenv()

async def analyze_product_ingredients(
    ingredients_data: List[IngredientAnalysisResult],
    user_preferences: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze multiple ingredients to provide a comprehensive product analysis
    for AR display, considering user preferences and dietary restrictions.
    """
    logger.info(f"Analyzing product with {len(ingredients_data)} ingredients")
    
    # Initialize LLM
    api_key = os.getenv("LLM_API_KEY")
    model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.0-flash")
    
    llm = ChatGoogleGenerativeAI(
        google_api_key=api_key,
        model=model_name,
        temperature=0.2  # Lower temperature for more factual responses
    )
    
    # Prepare ingredient data for the prompt
    ingredients_summary = []
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
    
    # Add user preferences context if available
    user_context = ""
    if user_preferences:
        allergies = user_preferences.get("allergies", "None specified")
        diet = user_preferences.get("dietary_restrictions", "None specified")
        user_context = f"""
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
2. Suitable Diet Types: Determine if this product is suitable for vegans, vegetarians, etc.
3. Allergy Warnings: Flag any potential allergens present
4. Usage Recommendations: Provide safe consumption limits or usage guidance
5. Health Insights: Summarize health benefits and concerns
6. Ingredient Interactions: Note any ingredients that may interact when combined
7. Key Takeaway: A single sentence summarizing if this product is recommended

## FORMAT YOUR RESPONSE AS JSON:
{{
  "overall_safety_score": (number between 1-10),
  "suitable_diet_types": (array of strings like "Vegan", "Vegetarian", etc.),
  "allergy_warnings": (array of strings),
  "usage_recommendations": (string with specific guidance),
  "health_insights": {{
    "benefits": (array of strings),
    "concerns": (array of strings)
  }},
  "ingredient_interactions": (array of strings),
  "key_takeaway": (string)
}}

Only include factual information based on the provided data. If information is unavailable for any field, use appropriate default values.
"""
    
    logger.info("Sending product analysis prompt to LLM")
    
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
                logger.info("Successfully parsed product analysis")
                return analysis
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                # Return a simplified analysis on error
                return {
                    "overall_safety_score": calculate_average_safety(ingredients_data),
                    "error": "Failed to parse complete analysis",
                    "ingredient_count": len(ingredients_data),
                    "key_takeaway": "Analysis error occurred, please check individual ingredients"
                }
        else:
            logger.error("Could not find JSON in LLM response")
            return {
                "overall_safety_score": calculate_average_safety(ingredients_data),
                "error": "Failed to generate structured analysis",
                "ingredient_count": len(ingredients_data)
            }
    
    except Exception as e:
        logger.error(f"Error in product analysis: {e}")
        # Fallback analysis based on simple calculations
        return generate_fallback_analysis(ingredients_data)


def calculate_average_safety(ingredients_data: List[IngredientAnalysisResult]) -> float:
    """Calculate average safety score from ingredients."""
    safety_scores = [i.safety_rating for i in ingredients_data if i.safety_rating is not None]
    if not safety_scores:
        return 5.0  # Default middle value
    return round(sum(safety_scores) / len(safety_scores), 1)


def generate_fallback_analysis(ingredients_data: List[IngredientAnalysisResult]) -> Dict[str, Any]:
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
        "key_takeaway": f"Product has {len(ingredients_data)} ingredients with average safety score of {safety_score}/10"
    }