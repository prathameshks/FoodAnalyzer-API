import asyncio
from functools import partial
import os
import json
import traceback
from dotenv import load_dotenv
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI

# modular
from interfaces.ingredientModels import IngredientAnalysisResult,IngredientState
from logger_manager import log_debug, log_error, log_info, log_warning
from utils.agent_tools import search_local_db,search_web,search_wikipedia,search_open_food_facts,search_usda,search_pubchem

# Load environment variables from .env file
load_dotenv()



def create_summary_from_source(source: Dict[str, Any]) -> str:
    """Create a meaningful summary from source data."""
    source_name = source.get("source", "Unknown")
    source_data = source.get("data")
    
    if not source_data:
        return "Data found but empty"
    
    # Handle different types of sources
    if source_name == "Local DB":
        if isinstance(source_data, dict):
            # Get the most informative fields from local DB
            return f"E-Number: {source_data.get('E No.', 'N/A')}, " \
                   f"Category: {source_data.get('Functional Class', 'N/A')}, " \
                   f"Description: {source_data.get('Main Use', '')[:100]}..."
    
    elif source_name == "DuckDuckGo":
        if isinstance(source_data, list) and source_data:
            # Get the first query and a snippet of the result
            first_result = source_data[0]
            query = first_result.get("query", "")
            result_snippet = first_result.get("result", "")[:150]
            return f"Query: '{query}', Result: '{result_snippet}...'"
    
    elif source_name == "Wikipedia":
        # For wikipedia, return the first paragraph
        if isinstance(source_data, str):
            first_paragraph = source_data.split("\n\n")[0][:200]
            return f"Wikipedia excerpt: {first_paragraph}..."
    
    elif source_name in ["Open Food Facts", "Open Food Facts Products"]:
        if isinstance(source_data, dict):
            # Try to extract product name or ingredient description
            if "product" in source_data:
                return f"Product info: {source_data.get('product', {}).get('product_name', 'Unknown')}"
            elif "ingredients_text" in source_data:
                return f"Ingredients: {source_data.get('ingredients_text', '')[:150]}..."
            else:
                return f"Found data with {len(source_data)} fields"
    
    elif source_name == "USDA FoodData Central":
        if isinstance(source_data, dict) and "foods" in source_data:
            foods = source_data.get("foods", [])
            if foods:
                first_food = foods[0]
                return f"Food: {first_food.get('description', 'Unknown')}, " \
                       f"Category: {first_food.get('foodCategory', 'N/A')}"
            else:
                return "Found USDA data, but no specific foods listed"
    
    elif source_name == "PubChem":
        if isinstance(source_data, dict):
            compound_info = source_data.get("compound_info", {})
            properties = source_data.get("properties", {})
            
            if "PC_Compounds" in compound_info and compound_info["PC_Compounds"]:
                compound = compound_info["PC_Compounds"][0]
                return f"Chemical ID: {compound.get('id', {}).get('id', {}).get('cid', 'N/A')}, " \
                       f"Found chemical property data"
    
    # Default for unknown or complex sources
    return f"Found data from {source_name} ({type(source_data).__name__})"

def analyze_ingredient(state: IngredientState) -> IngredientState:
    """Analyze ingredient data with LLM to generate structured information.
    
    Takes the current state with collected sources_data and uses an LLM to generate
    a comprehensive analysis of the ingredient including safety rating, health effects,
    description, and alternate names.
    
    Args:
        state: The current IngredientState containing all collected data
        
    Returns:
        Updated state with analysis results
    """
    # Get API key and model from environment
    api_key = os.getenv("GOOGLE_API_KEY")
    model_name = os.getenv("LLM_MODEL_NAME", "gemini-1.5-pro")
    
    # Basic validation
    if not api_key:
        log_error("No Google API key found in environment variables")
        new_state = state.copy()
        new_state["result"] = {
            "name": state["ingredient"],
            "is_found": False,
            "description": "Error: Missing API credentials for analysis"
        }
        new_state["analysis_done"] = True
        new_state["status"] = "analysis_error"
        return new_state
    
    # Initialize LLM
    try:
        llm = ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model_name,
            temperature=0.3,  # Lower temperature for more factual responses
            # convert_system_message_to_human=True
        )
    except Exception as e:
        log_error(f"Error initializing LLM: {e}",e)
        new_state = state.copy()
        new_state["result"] = {
            "name": state["ingredient"],
            "is_found": False,
            "description": f"Error initializing LLM: {str(e)}"
        }
        new_state["analysis_done"] = True
        new_state["status"] = "analysis_error"
        return new_state
    
    # Get sources from state
    sources_data = state["sources_data"]
    log_info(f"Analyzing ingredient with {len(sources_data)} total sources")
    
    # Filter for successful sources only
    found_sources = [source for source in sources_data if source.get('found', False)]
    log_info(f"Found {len(found_sources)} sources with usable data")
    
    # Create default result structure
    result = {
        "name": state["ingredient"],
        "alternate_names": [],
        "is_found": len(found_sources) > 0,
        "safety_rating": 5,  # Default middle rating
        "description": "No reliable information found." if not found_sources else "",
        "health_effects": ["Unknown - insufficient data"] if not found_sources else [],
        "details_with_source": [
            {
                "source": source.get("source", "Unknown"),
                "found": source.get("found", False),
                "summary": create_summary_from_source(source) if source.get("found", False) else "No data found",
            }
            for source in sources_data
        ]
    }
    
    # If we have data, analyze it
    if found_sources:
        # Format source data for the prompt
        source_texts = []
        for i, source in enumerate(found_sources):
            source_name = source.get('source', f'Source {i+1}')
            source_data = source.get('data')
            
            # Process different data formats appropriately
            try:
                if isinstance(source_data, dict):
                    source_text = format_dict_source(source_name, source_data)
                elif isinstance(source_data, list):
                    source_text = format_list_source(source_name, source_data)
                elif isinstance(source_data, str):
                    # For string data, include as is (limiting length)
                    source_text = f"--- {source_name} ---\n{source_data[:1500]}"
                else:
                    # For other types, convert to string
                    source_text = f"--- {source_name} ---\n{str(source_data)[:1000]}"
                
                source_texts.append(source_text)
            except Exception as e:
                log_error(f"Error formatting source {source_name}: {e}",e)
                source_texts.append(f"--- {source_name} ---\nError formatting data: {str(e)}")
        
        # Combine all source texts
        combined_data = "\n\n".join(source_texts)
        log_info(f"Combined data for analysis:\n{combined_data[:500]}...(truncated)")
        
        # Create the analysis prompt
        analysis_prompt = f"""
        Task: Analyze food ingredient data and provide a structured assessment.
        
        Ingredient: {state["ingredient"]}
        
        Based on the following data sources, provide:
        1. Safety rating (scale 1-10, where 1=unsafe for consumption, 5=moderate concerns, 10=very safe)
        2. List of potential health effects (both positive & negative, maximum 5 points)
        3. Brief description of what this ingredient is, how it's used, and its properties
        4. Alternative names for this ingredient
        5. Allergic information of the ingredient like which type of allergies we can got, etc.
        6. Diet Type of that ingredient like Vegan, Vegetarian, Non-Vegetarian
        
        Available data:
        {combined_data}
        
        Format your response as a JSON object with these keys:
        - "safety_rating": (number between 1-10)
        - "health_effects": (array of strings)
        - "description": (string)
        - "alternate_names": (array of strings)
        - "allergic_info": (array of strings)
        - "diet_type" : (string from vegan,vegetarian,non-vegetarian,unknown)
        
        Only include factual information supported by the provided data. If information is 
        unavailable for any field, use appropriate default values. But if information is too obvious you can fill appropriate information just make sure only relevant data is there in the output.
        """
        
        # Process with LLM
        try:
            log_info("Sending analysis prompt to LLM")
            llm_response = llm.invoke(analysis_prompt)
            log_info("Received LLM response")
            
            # Extract and parse JSON from LLM response
            try:
                analysis_text = llm_response.content
                log_debug(f"LLM response: {analysis_text[:500]}...(truncated)")
                
                # Find JSON in the response
                start_idx = analysis_text.find('{')
                end_idx = analysis_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = analysis_text[start_idx:end_idx]
                    analysis = json.loads(json_str)
                    
                    # Update result with analyzed data
                    result.update({
                        "safety_rating": analysis.get("safety_rating", 5),
                        "description": analysis.get("description", "No description available."),
                        "health_effects": analysis.get("health_effects", []),
                        "alternate_names": analysis.get("alternate_names", []),
                        "allergic_info": analysis.get("allergic_info", []),
                        "diet_type": analysis.get("diet_type", "unknown"),
                    })
                    log_info(f"Analysis complete - Safety Rating: {result['safety_rating']}")
                else:
                    log_warning("Could not find JSON in LLM response")
                    result["description"] = "Error: Failed to parse LLM analysis output."
            except json.JSONDecodeError as e:
                log_error(f"JSON parsing error: {e}",e)
                result["description"] = f"Error parsing analysis: {str(e)}"
                
        except Exception as e:
            log_error(f"Error in LLM analysis: {e}",e)
            log_error(traceback.format_exc())
            result.update({
                "description": f"Error in analysis: {str(e)}",
                "health_effects": ["Error in analysis"],
            })
    
    # Update state with results
    new_state = state.copy()
    new_state["result"] = result
    new_state["analysis_done"] = True
    new_state["status"] = "analysis_complete"
    return new_state

def format_dict_source(source_name: str, source_data: dict) -> str:
    """Format dictionary source data for LLM consumption."""
    source_text = f"--- {source_name} ---\n"
    
    # Handle different sources appropriately
    if source_name == "Local DB":
        relevant_keys = [k for k in source_data.keys()]
        for key in relevant_keys:
            source_text += f"{key}: {source_data[key]}\n"
    elif source_name == "DuckDuckGo":
        if isinstance(source_data, list):
            for item in source_data:
                source_text += f"Query: {item.get('query', '')}\n"
                source_text += f"Summary: {item.get('result', '')[:500]}...\n"
    elif source_name in ["Open Food Facts", "USDA FoodData Central"]:
        # Extract key info for food databases
        if "ingredients_text" in source_data:
            source_text += f"Ingredients: {source_data['ingredients_text']}\n"
        if "description" in source_data:
            source_text += f"Description: {source_data['description']}\n"
        if "categories" in source_data:
            source_text += f"Categories: {source_data['categories']}\n"
        # Include top-level fields only
        for key, value in source_data.items():
            if not isinstance(value, (dict, list)) and key not in ["ingredients_text", "description", "categories"]:
                source_text += f"{key}: {value}\n"
    elif source_name == "PubChem":
        # Extract key chemical information
        if "compound_info" in source_data:
            source_text += "Chemical information:\n"
            compound_data = source_data.get("compound_info", {})
            if "PC_Compounds" in compound_data and len(compound_data["PC_Compounds"]) > 0:
                compound = compound_data["PC_Compounds"][0]
                source_text += f"Compound ID: {compound.get('id', {}).get('id', {}).get('cid', 'N/A')}\n"
        
        if "properties" in source_data and source_data["properties"]:
            properties = source_data["properties"]
            if "PropertyTable" in properties:
                prop_table = properties["PropertyTable"]
                if "Properties" in prop_table and len(prop_table["Properties"]) > 0:
                    props = prop_table["Properties"][0]
                    source_text += "Properties:\n"
                    for key, value in props.items():
                        source_text += f"{key}: {value}\n"
    else:
        # Generic dictionary handling for other sources
        for key, value in source_data.items():
            if not isinstance(value, (dict, list)) or len(str(value)) < 100:
                source_text += f"{key}: {value}\n"
            else:
                source_text += f"{key}: [Complex data]\n"
    
    return source_text

def format_list_source(source_name: str, source_data: list) -> str:
    """Format list source data for LLM consumption."""
    source_text = f"--- {source_name} ---\n"
    
    # Handle different list structures
    if len(source_data) > 0:
        if isinstance(source_data[0], dict):
            # List of dictionaries
            source_text += f"Found {len(source_data)} items:\n"
            for i, item in enumerate(source_data[:3]):  # Limit to first 3 items
                source_text += f"Item {i+1}:\n"
                for key, value in item.items():
                    if not isinstance(value, (dict, list)):
                        source_text += f"  {key}: {value}\n"
        else:
            # List of other types
            source_text += f"Data points ({len(source_data)}):\n"
            for i, item in enumerate(source_data[:5]):  # Limit to first 5 items
                source_text += f"{i+1}. {str(item)[:200]}\n"
    else:
        source_text += "Empty list\n"
    
    return source_text

class IngredientInfoAgentLangGraph:
    async def _fetch_data_from_source(self, tool_func, ingredient: str) -> Dict[str, Any]:
        """Fetch data from a single source asynchronously."""
        # Get tool name safely - handle both function tools and structured tools
        if hasattr(tool_func, "name"):
            # For structured tools
            tool_name = tool_func.name
        elif hasattr(tool_func, "__name__"):
            # For function tools
            tool_name = tool_func.__name__
        else:
            # Fallback
            tool_name = str(tool_func).split()[0]
        
        source_name = tool_name.replace("search_", "").replace("_", " ").title()
        log_info(f"Searching {source_name} for {ingredient}")
        
        try:
            # Run the tool function in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, partial(tool_func.invoke, ingredient))
            
            if result.get("found", False):
                log_info(f"{source_name} found data for {ingredient}")
            return result
        except Exception as e:
            log_error(f"Error in {source_name} search: {e}",e)
            return {"source": source_name, "found": False, "error": str(e)}
    
    async def process_ingredient_async(self, ingredient: str) -> IngredientAnalysisResult:
        """Process an ingredient using parallel data fetching."""
        log_info(f"=== Parallel processing for: {ingredient} ===")
        
        # Define all the tools to run in parallel
        tools = [
            search_local_db,
            search_web,
            search_wikipedia,
            search_open_food_facts,
            search_usda,
            search_pubchem
        ]
        
        # Create tasks for each tool
        tasks = [self._fetch_data_from_source(tool, ingredient) for tool in tools]
        
        # Run all tasks concurrently and collect results
        results = await asyncio.gather(*tasks)
        
        # Filter for successful results
        sources_data = [result for result in results if not result.get("error")]
        
        # Create a state for analysis
        state = {
            "ingredient": ingredient,
            "sources_data": sources_data,
            "result": None,
            "status": "ready_for_analysis",
            "analysis_done": False,
            "local_db_checked": True,
            "web_search_done": True,
            "wikipedia_checked": True,
            "open_food_facts_checked": True,
            "usda_checked": True,
            "pubchem_checked": True
        }
        
        # Run the analysis with the collected data
        final_state = analyze_ingredient(state)
        
        # Extract the result or create a default
        if final_state.get("result"):
            log_info(f"Analysis complete for {ingredient}")
            return IngredientAnalysisResult(**final_state["result"])
        else:
            log_info(f"No result in final state for {ingredient}, returning default")
            return IngredientAnalysisResult(
                name=ingredient, 
                is_found=len(sources_data) > 0, 
                details_with_source=sources_data
            )
        
    def process_ingredient(self, ingredient: str) -> IngredientAnalysisResult:
        """
        Process an ingredient using direct sequential approach instead of async.
        This method provides compatibility with synchronous code.
        """
        log_info(f"=== Sequential processing for: {ingredient} ===")
        
        # Initialize empty sources data
        sources_data = []
        
        # Run each tool directly in sequence and collect results
        log_info(f"Searching local database for {ingredient}")
        result = search_local_db.invoke(ingredient)

        if result.get("found", False):
            sources_data.append(result)
            log_info(f"Local DB found data for {ingredient}")
        
        log_info(f"Searching web for {ingredient}")
        result = search_web.invoke(ingredient)
        if result.get("found", False):
            sources_data.append(result)
            log_info(f"Web search found data for {ingredient}")
        
        log_info(f"Searching Wikipedia for {ingredient}")
        result = search_wikipedia.invoke(ingredient)
        if result.get("found", False):
            sources_data.append(result)
            log_info(f"Wikipedia found data for {ingredient}")
        
        log_info(f"Searching Open Food Facts for {ingredient}")
        result = search_open_food_facts.invoke(ingredient)
        if result.get("found", False):
            sources_data.append(result)
            log_info(f"Open Food Facts found data for {ingredient}")
        
        
        log_info(f"Searching USDA for {ingredient}")
        result = search_usda.invoke(ingredient)
        if result.get("found", False):
            sources_data.append(result)
            log_info(f"USDA found data for {ingredient}")
        
        log_info(f"Searching PubChem for {ingredient}")
        result = search_pubchem.invoke(ingredient)
        if result.get("found", False):
            sources_data.append(result)
            log_info(f"PubChem found data for {ingredient}")
        
        state = IngredientState(ingredient=ingredient,
                                 sources_data=sources_data,
                                 status="ready_for_analysis"
                                 )
        
        # Run the analysis with the collected data
        final_state = analyze_ingredient(state)
        
        # Extract the result or create a default
        if final_state.get("result"):
            log_info(f"Analysis complete for {ingredient}")

            return IngredientAnalysisResult(**final_state["result"])
        else:
            log_info(f"No result in final state for {ingredient}, returning default")
            return IngredientAnalysisResult(
                name=ingredient, 
                is_found=len(sources_data) > 0, 
                details_with_source=sources_data
            )
        
if __name__ == "__main__":
    agent = IngredientInfoAgentLangGraph()
    
    # Use the simple method that works reliably
    result = agent.process_ingredient("SODIUM TRIPOLYPHOSPHATE")
    print(json.dumps(result.model_dump(), indent=2))
    
    benzoate_result = agent.process_ingredient("Sodium Benzoate")
    print(json.dumps(benzoate_result.model_dump(), indent=2))