import asyncio
import os

import pandas as pd
from dotenv import load_dotenv

from typing import Dict, Any
# modular
from logger_manager import log_error, log_info, log_warning
from dotenv import load_dotenv

import aiohttp
import time
import requests

from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_core.tools import tool


# Load environment variables from .env file
load_dotenv()

# Load Scraped Database
SCRAPED_DB_PATH = "data/Food_Aditives_E_numbers.csv"  # Ensure this file exists
if os.path.exists(SCRAPED_DB_PATH):
    additives_df = pd.read_csv(SCRAPED_DB_PATH)
    log_info(f"Loaded database with {len(additives_df)} entries")
else:
    additives_df = None
    log_warning("Scraped database not found!")


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
    log_info(f"Searching local DB for: {ingredient}")
    if additives_df is not None:
        match = additives_df[additives_df['Name of Additive'].str.contains(ingredient, case=False, na=False, regex=False)]
        if not match.empty:
            return {"source": "Local DB", "found": True, "data": match.iloc[0].to_dict()}
    return {"source": "Local DB", "found": False, "data": None}

@tool("search_open_food_facts")
def search_open_food_facts(ingredient: str) -> Dict[str, Any]:
    """Search Open Food Facts database for ingredient information."""
    log_info(f"Searching Open Food Facts for: {ingredient}")
    
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
        log_error(f"Error searching Open Food Facts: {e}",e)
        return {"source": "Open Food Facts", "found": False, "error": str(e)}

@tool("search_usda")
def search_usda(ingredient: str) -> Dict[str, Any]:
    """Search USDA FoodData Central for ingredient information."""
    log_info(f"Searching USDA for: {ingredient}")
    
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
        log_error(f"Error searching USDA: {e}",e)
        return {"source": "USDA FoodData Central", "found": False, "error": str(e)}

async def async_search_pubchem(ingredient: str) -> Dict[str, Any]:
    """Asynchronously search PubChem for chemical information about the ingredient."""
    log_info(f"Searching PubChem for: {ingredient}")
    
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
                            log_warning(f"PubChem returned status: {response.status} for URL: {url}")
                            return None
                except asyncio.TimeoutError:
                    if retry_count < PUBCHEM_MAX_RETRIES:
                        delay = (2 ** retry_count) * 5  # Exponential backoff
                        log_warning(f"PubChem timeout for URL '{url}'. Retrying in {delay:.2f} seconds (attempt {retry_count + 1}/{PUBCHEM_MAX_RETRIES})")
                        await asyncio.sleep(delay)
                        return await fetch_data(url, timeout, retry_count + 1)  # Recursive retry
                    else:
                        log_error(f"Max retries reached for PubChem timeout on URL: {url}",asyncio.TimeoutError)
                        return None
                except Exception as e:
                    log_error(f"PubChem error for URL '{url}': {e}",e)
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
        log_error(f"Error searching PubChem: {e}",e)
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
    log_info(f"Searching Wikipedia for: {ingredient}")
    
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
        log_error(f"Error searching Wikipedia: {e}",e)
        return {"source": "Wikipedia", "found": False, "error": str(e)}

@tool("search_web")
def search_web(ingredient: str) -> Dict[str, Any]:
    """Search web for ingredient information using DuckDuckGo."""
    log_info(f"Searching web for: {ingredient}")
    
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
        log_error(f"Web search error: {e}",e)
        return {"source": "DuckDuckGo", "found": False, "error": str(e)}
