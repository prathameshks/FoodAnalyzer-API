from fastapi import FastAPI, HTTPException
from routers.auth import router as auth_router
from routers.analysis import router as analysis_router
from routers.history import router as history_router
from database import get_db, engine
from models.base import Base
from services.logging_service import log_info, log_error

app = FastAPI()
db = get_db()

@app.on_event("startup")
async def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        log_info("Database tables created successfully.")
    except Exception as e:
        log_error(f"Error creating database tables: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating database tables")

app.include_router(analysis_router, prefix="/api/analyze")
app.include_router(auth_router, prefix="/api/auth")
app.include_router(history_router, prefix="/api/history")

# To run the FastAPI app, use the command: uvicorn main:app --reload
