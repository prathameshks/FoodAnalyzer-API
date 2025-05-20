import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# Environment variables for FoodAnalyzer-API
PORT = int(os.getenv("PORT", 8000))

# JWT Secret Key
SECRET_KEY = os.getenv("SECRET_KEY", "09d8f7a6b5c4e3d2f1a0b9c8d7e6f5a4")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# Hugging Face Transformers API key not required
# HUGGING_FACE_API_KEY = os.getenv("HUGGING_FACE_API_KEY", None)
# OpenAI API key not required
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)

# API keys and model names for different LLMs here 
# for google ai studio
LLM_API_KEY = os.getenv("LLM_API_KEY", None)
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-2.0-flash")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", None)
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", None)

USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")

# pg db url
DATABASE_URL = os.getenv("DATABASE_URL", None)

# Vuforia keys
VUFORIA_SERVER_ACCESS_KEY = os.getenv("VUFORIA_SERVER_ACCESS_KEY", None)
VUFORIA_SERVER_SECRET_KEY = os.getenv("VUFORIA_SERVER_SECRET_KEY", None)
VUFORIA_TARGET_DATABASE_NAME = os.getenv("VUFORIA_TARGET_DATABASE_NAME", "FoodAnalyzer_BE_PROJ")
VUFORIA_TARGET_DATABASE_ID = os.getenv("VUFORIA_TARGET_DATABASE_ID", "FoodAnalyzer_BE_PROJ")

# langsmith keys optional
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", True)
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", None)
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", None)

# app settings
PARALLEL_RATE_LIMIT = int(os.getenv("PARALLEL_RATE_LIMIT", 10))

# Rate limiting configuration in seconds
PUBCHEM_TIMEOUT = int(os.getenv("PUBCHEM_TIMEOUT", 2))
PUBCHEM_MAX_RETRIES = int(os.getenv("PUBCHEM_MAX_RETRIES", 2))

# Delay in seconds
DUCKDUCKGO_RATE_LIMIT_DELAY = int(os.getenv("DUCKDUCKGO_RATE_LIMIT_DELAY", 2))
DUCKDUCKGO_MAX_RETRIES = int(os.getenv("DUCKDUCKGO_MAX_RETRIES", 2))

# fake response for testing
SEND_FAKE_TARGET = os.getenv("SEND_FAKE_TARGET", False) == "true"
FAKE_TARGET_IMAGE_NAME = os.getenv("FAKE_TARGET_IMAGE_NAME", "detected_Snack_0.13_db8318a668504073ad5fd0677187d305.jpg")

# Define Required Environment Variables and show error if not set
required_env_vars = {
    "LLM_API_KEY":LLM_API_KEY,
    "GOOGLE_API_KEY":GOOGLE_API_KEY,
    "GOOGLE_CSE_ID":GOOGLE_CSE_ID,
    "USDA_API_KEY":USDA_API_KEY,
    "DATABASE_URL":DATABASE_URL,
    "VUFORIA_SERVER_ACCESS_KEY":VUFORIA_SERVER_ACCESS_KEY,
    "VUFORIA_SERVER_SECRET_KEY":VUFORIA_SERVER_SECRET_KEY,
    "VUFORIA_TARGET_DATABASE_NAME":VUFORIA_TARGET_DATABASE_NAME,
    "VUFORIA_TARGET_DATABASE_ID":VUFORIA_TARGET_DATABASE_ID,
}

# Check if all required environment variables are set
for var in required_env_vars.keys():
    if required_env_vars[var] is None:
        raise ValueError(f"Environment variable {var} is not set. Please set it in the .env file.")