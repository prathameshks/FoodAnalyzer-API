import asyncio
from functools import partial
import os
import json
import traceback
import requests
import pandas as pd
from dotenv import load_dotenv
import aiohttp
import time

from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_core.tools import tool

# modular
from logger_manager import logger
from interfaces.ingredientModels import IngredientAnalysisResult,IngredientState

# Load environment variables from .env file
load_dotenv()

# Load Scraped Database
SCRAPED_DB_PATH = "data/Food_Aditives_E_numbers.csv"  # Ensure this file exists
if os.path.exists(SCRAPED_DB_PATH):
    additives_df = pd.read_csv(SCRAPED_DB_PATH)
    logger.info(f"Loaded database with {len(additives_df)} entries")
else:
    additives_df = None
    logger.warning("Scraped database not found!")


# Define a rate limit (adjust as needed)
PUBCHEM_TIMEOUT = float(os.getenv("PUBCHEM_TIMEOUT", "2.0"))   # seconds
PUBCHEM_MAX_RETRIES = int(os.getenv("PUBCHEM_MAX_RETRIES", "3"))  # Max retries

# Rate limiting configuration
DUCKDUCKGO_RATE_LIMIT_DELAY = float(os.getenv("DUCKDUCKGO_RATE_LIMIT_DELAY", "2.0"))  # Delay in seconds
DUCKDUCKGO_MAX_RETRIES = int(os.getenv("DUCKDUCKGO_MAX_RETRIES", "3"))  # Max retries


# Define tool functions
@tool("search_local_db")
def search_local_db(ingredient: str) -> Dict[str, Any]:
    """Search local database for ingredient information. E number database scrapped"""
    logger.info(f"Searching local DB for: {ingredient}")
    if additives_df is not None:
        match = additives_df[additives_df['Name of Additive'].str.contains(ingredient, case=False, na=False, regex=False)]
        if not match.empty:
            return {"source": "Local DB", "found": True, "data": match.iloc[0].to_dict()}
    return {"source": "Local DB", "found": False, "data": None}

@tool("search_open_food_facts")
def search_open_food_facts(ingredient: str) -> Dict[str, Any]:
    """Search Open Food Facts database for ingredient information."""
    logger.info(f"Searching Open Food Facts for: {ingredient}")
    
    try:
        open_food_facts_api = "https://world.openfoodfacts.org/api/v0"
        # Search for the ingredient
        search_url = f"{open_food_facts_api}/ingredient/{ingredient.lower().replace(' ', '-')}.json"
        response = requests.get(search_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 1:  # Successfully found
                return {
                    "source": "Open Food Facts",
                    "found": True,
                    "data": data
                }
        
        # Try searching products containing this ingredient
        product_search_url = f"{open_food_facts_api}/search.json?ingredients_tags={ingredient.lower().replace(' ', '_')}&page_size=5"
        response = requests.get(product_search_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("count") > 0:
                return {
                    "source": "Open Food Facts Products",
                    "found": True,
                    "data": data
                }
        
        return {"source": "Open Food Facts", "found": False, "data": None}
    
    except Exception as e:
        logger.error(f"Error searching Open Food Facts: {e}")
        return {"source": "Open Food Facts", "found": False, "error": str(e)}

@tool("search_usda")
def search_usda(ingredient: str) -> Dict[str, Any]:
    """Search USDA FoodData Central for ingredient information."""
    logger.info(f"Searching USDA for: {ingredient}")
    
    try:
        usda_api = "https://api.nal.usda.gov/fdc/v1"
        usda_api_key = os.getenv("USDA_API_KEY", "DEMO_KEY")  # Use DEMO_KEY if not provided
        
        # Search for the ingredient
        search_url = f"{usda_api}/foods/search"
        params = {
            "api_key": usda_api_key,
            "query": ingredient,
            "dataType": ["Foundation", "SR Legacy", "Branded"],
            "pageSize": 5
        }
        
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("totalHits", 0) > 0:
                return {
                    "source": "USDA FoodData Central",
                    "found": True,
                    "data": data
                }
        
        return {"source": "USDA FoodData Central", "found": False, "data": None}
    
    except Exception as e:
        logger.error(f"Error searching USDA: {e}")
        return {"source": "USDA FoodData Central", "found": False, "error": str(e)}

async def async_search_pubchem(ingredient: str) -> Dict[str, Any]:
    """Asynchronously search PubChem for chemical information about the ingredient."""
    logger.info(f"Searching PubChem for: {ingredient}")
    
    try:
        pubchem_api = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data"
        # https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest#section=Input
        
        async with aiohttp.ClientSession() as session:
            # First try to get compound information by name
            search_url = f"{pubchem_api}/compound/name/{ingredient}/JSON"
            
            async def fetch_data(url: str, timeout: int = PUBCHEM_TIMEOUT, retry_count: int = 0):
                try:
                    async with session.get(url, timeout=timeout) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logger.warning(f"PubChem returned status: {response.status} for URL: {url}")
                            return None
                except asyncio.TimeoutError:
                    if retry_count < PUBCHEM_MAX_RETRIES:
                        delay = (2 ** retry_count) * 5  # Exponential backoff
                        logger.warning(f"PubChem timeout for URL '{url}'. Retrying in {delay:.2f} seconds (attempt {retry_count + 1}/{PUBCHEM_MAX_RETRIES})")
                        await asyncio.sleep(delay)
                        return await fetch_data(url, timeout, retry_count + 1)  # Recursive retry
                    else:
                        logger.error(f"Max retries reached for PubChem timeout on URL: {url}")
                        return None
                except Exception as e:
                    logger.error(f"PubChem error for URL '{url}': {e}")
                    return None
            
            data = await fetch_data(search_url)
            
            if data and "PC_Compounds" in data:
                compound_id = data["PC_Compounds"][0]["id"]["id"]["cid"]
                
                # Get more detailed information using the CID
                property_url = f"{pubchem_api}/compound/cid/{compound_id}/property/MolecularFormula,MolecularWeight,IUPACName,InChI,InChIKey,CanonicalSMILES/JSON"
                properties_data = await fetch_data(property_url)
                
                # Get classifications and categories
                classification_url = f"{pubchem_api}/compound/cid/{compound_id}/classification/JSON"
                classification_data = await fetch_data(classification_url)
                
                return {
                    "source": "PubChem",
                    "found": True,
                    "data": {
                        "compound_info": data,
                        "properties": properties_data,
                        "classification": classification_data
                    }
                }
            
            return {"source": "PubChem", "found": False, "data": None}
    
    except Exception as e:
        logger.error(f"Error searching PubChem: {e}")
        return {"source": "PubChem", "found": False, "error": str(e)}

@tool("search_pubchem")
def search_pubchem(ingredient: str) -> Dict[str, Any]:
    """Search PubChem for chemical information about the ingredient."""
    # Use asyncio.run to handle the async operation from synchronous code
    try:
        # For Python 3.7+
        return asyncio.run(async_search_pubchem(ingredient))
    except RuntimeError:
        # If already in an event loop (e.g., in FastAPI)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(async_search_pubchem(ingredient))
    
@tool("search_wikipedia")
def search_wikipedia(ingredient: str) -> Dict[str, Any]:
    """Search Wikipedia for ingredient information."""
    logger.info(f"Searching Wikipedia for: {ingredient}")
    
    try:
        wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
        wiki_result = wikipedia.run(ingredient)
        
        if wiki_result and len(wiki_result) > 100:  # Only count substantial results
            return {
                "source": "Wikipedia",
                "found": True,
                "data": wiki_result
            }
        else:
            # Try with more specific searches
            food_wiki = wikipedia.run(f"{ingredient} food additive")
            if food_wiki and len(food_wiki) > 100:
                return {
                    "source": "Wikipedia",
                    "found": True,
                    "data": food_wiki
                }
            
            chemical_wiki = wikipedia.run(f"{ingredient} chemical compound")
            if chemical_wiki and len(chemical_wiki) > 100:
                return {
                    "source": "Wikipedia",
                    "found": True,
                    "data": chemical_wiki
                }
        
        return {"source": "Wikipedia", "found": False, "data": None}
    
    except Exception as e:
        logger.error(f"Error searching Wikipedia: {e}")
        return {"source": "Wikipedia", "found": False, "error": str(e)}

@tool("search_web")
def search_web(ingredient: str) -> Dict[str, Any]:
    """Search web for ingredient information using DuckDuckGo."""
    logger.info(f"Searching web for: {ingredient}")
    
    try:
        duckduckgo = DuckDuckGoSearchRun()
        search_queries = [f"{ingredient} food ingredient safety", f"{ingredient} E-number food additive",f"{ingredient}'s allergic information",f"is {ingredient} vegan,vegetarian or Non-vegetarian"]
        all_results = []
        for query in search_queries:
            time.sleep(DUCKDUCKGO_RATE_LIMIT_DELAY)
            result = duckduckgo.run(query)
            if result:
                all_results.append({"query": query, "result": result})
        return {"source": "DuckDuckGo", "found": bool(all_results), "data": all_results}
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return {"source": "DuckDuckGo", "found": False, "error": str(e)}

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
        logger.error("No Google API key found in environment variables")
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
        logger.error(f"Error initializing LLM: {e}")
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
    logger.info(f"Analyzing ingredient with {len(sources_data)} total sources")
    
    # Filter for successful sources only
    found_sources = [source for source in sources_data if source.get('found', False)]
    logger.info(f"Found {len(found_sources)} sources with usable data")
    
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
                logger.error(f"Error formatting source {source_name}: {e}")
                source_texts.append(f"--- {source_name} ---\nError formatting data: {str(e)}")
        
        # Combine all source texts
        combined_data = "\n\n".join(source_texts)
        logger.info(f"Combined data for analysis:\n{combined_data[:500]}...(truncated)")
        
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
            logger.info("Sending analysis prompt to LLM")
            llm_response = llm.invoke(analysis_prompt)
            logger.info("Received LLM response")
            
            # Extract and parse JSON from LLM response
            try:
                analysis_text = llm_response.content
                logger.debug(f"LLM response: {analysis_text[:500]}...(truncated)")
                
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
                    logger.info(f"Analysis complete - Safety Rating: {result['safety_rating']}")
                else:
                    logger.warning("Could not find JSON in LLM response")
                    result["description"] = "Error: Failed to parse LLM analysis output."
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                result["description"] = f"Error parsing analysis: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            logger.error(traceback.format_exc())
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
        logger.info(f"Searching {source_name} for {ingredient}")
        
        try:
            # Run the tool function in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, partial(tool_func.invoke, ingredient))
            
            if result.get("found", False):
                logger.info(f"{source_name} found data for {ingredient}")
            return result
        except Exception as e:
            logger.error(f"Error in {source_name} search: {e}")
            return {"source": source_name, "found": False, "error": str(e)}
    
    async def process_ingredient_async(self, ingredient: str) -> IngredientAnalysisResult:
        """Process an ingredient using parallel data fetching."""
        logger.info(f"=== Parallel processing for: {ingredient} ===")
        
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
            logger.info(f"Analysis complete for {ingredient}")
            return IngredientAnalysisResult(**final_state["result"])
        else:
            logger.info(f"No result in final state for {ingredient}, returning default")
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
        logger.info(f"=== Sequential processing for: {ingredient} ===")
        
        # Initialize empty sources data
        sources_data = []
        
        # Run each tool directly in sequence and collect results
        logger.info(f"Searching local database for {ingredient}")
        result = search_local_db.invoke(ingredient)
        if result.get("found", False):
            sources_data.append(result)
            logger.info(f"Local DB found data for {ingredient}")
        
        logger.info(f"Searching web for {ingredient}")
        result = search_web.invoke(ingredient)
        if result.get("found", False):
            sources_data.append(result)
            logger.info(f"Web search found data for {ingredient}")
        
        logger.info(f"Searching Wikipedia for {ingredient}")
        result = search_wikipedia.invoke(ingredient)
        if result.get("found", False):
            sources_data.append(result)
            logger.info(f"Wikipedia found data for {ingredient}")
        
        logger.info(f"Searching Open Food Facts for {ingredient}")
        result = search_open_food_facts.invoke(ingredient)
        if result.get("found", False):
            sources_data.append(result)
            logger.info(f"Open Food Facts found data for {ingredient}")
        
        
        logger.info(f"Searching USDA for {ingredient}")
        result = search_usda.invoke(ingredient)
        if result.get("found", False):
            sources_data.append(result)
            logger.info(f"USDA found data for {ingredient}")
        
        logger.info(f"Searching PubChem for {ingredient}")
        result = search_pubchem.invoke(ingredient)
        if result.get("found", False):
            sources_data.append(result)
            logger.info(f"PubChem found data for {ingredient}")
        
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
            logger.info(f"Analysis complete for {ingredient}")
            return IngredientAnalysisResult(**final_state["result"])
        else:
            logger.info(f"No result in final state for {ingredient}, returning default")
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