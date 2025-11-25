from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from routers.auth import router as auth_router
from routers.analysis import router as analysis_router
from routers.history import router as history_router
from routers.product import router as product_router
import os
import uvicorn
from pathlib import Path
import tensorflow as tf
import tensorflow_hub as hub
from env import PORT, CORS_ORIGINS
from logger_manager import log_info


# Define the templates directory
templates = Jinja2Templates(directory="templates")

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0=all, 1=no INFO, 2=no WARNING, 3=no ERROR

# Use lifespan context manager instead of deprecated on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load TensorFlow model once during startup
    log_info("Loading TensorFlow model...")
    app.state.detector = hub.load("https://tfhub.dev/google/openimages_v4/ssd/mobilenet_v2/1").signatures['default']
    log_info("TensorFlow model loaded successfully!")
    yield
    # Shutdown: cleanup if needed
    log_info("Shutting down...")

app = FastAPI(
    title="FoodAnalyzer API",
    description="API for analyzing food products and their ingredients",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS - origins configurable via environment variable
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return RedirectResponse("/api")

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy", "version": "1.0.0"}

# print every request data for request using middleware

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Store the body content before sending to the next handler
    body_content = await request.body()
    # Create a new request with the consumed body
    request._body = body_content
    response = await call_next(request)
    log_info(f"Request: {request.method} {request.url}")
    return response

@app.get("/api", response_class=HTMLResponse)
async def read_api(request: Request):
    return templates.TemplateResponse("api_docs.html", {"request": request})

app.include_router(analysis_router, prefix="/api/analyze", tags=["Analysis"])
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(product_router, prefix="/api/product", tags=["Product"])
app.include_router(history_router, prefix="/api/history", tags=["History"])

# To run the FastAPI app, use the command: uvicorn main:app --reload
if __name__ == "__main__":
    # run using fastapi directly for development purposes
    uvicorn.run(app, host="0.0.0.0", port=PORT)