from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from routers.auth import router as auth_router
from routers.analysis import router as analysis_router
from routers.history import router as history_router
from routers.product import router as product_router
from dotenv import load_dotenv
import os
import uvicorn
from pathlib import Path

load_dotenv()
# Load environment variables from .env file
PORT = os.getenv("PORT", 8000)

# Define the templates directory
templates = Jinja2Templates(directory="templates")

app = FastAPI()

@app.get("/")
def read_root():
    return RedirectResponse("/api")

# print every request data for request using middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Store the body content before sending to the next handler
    body_content = await request.body()
    # Create a new request with the consumed body
    request._body = body_content
    response = await call_next(request)
    print(f"Request: {request.method} {request.url}")
    print(f"Data: {body_content}")
    print(f"Headers: {request.headers}")
    return response

@app.get("/api", response_class=HTMLResponse)
async def read_api(request: Request):
    return templates.TemplateResponse("api_docs.html", {"request": request})

app.include_router(analysis_router, prefix="/api/analyze")
app.include_router(auth_router, prefix="/api/auth")
app.include_router(product_router, prefix="/api/product")
app.include_router(history_router, prefix="/api/history")

app.add_event_handler("startup", lambda: print("Starting up..."))

# To run the FastAPI app, use the command: uvicorn main:app --reload
if __name__ == "__main__":
    # run using fastapi directly for development purposes
    uvicorn.run(app, host="0.0.0.0", port=PORT)