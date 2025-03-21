from fastapi import FastAPI
from routers.auth import router as auth_router
from routers.analysis import router as analysis_router
from routers.history import router as history_router
from database import get_db,engine
from models.base import Base

app = FastAPI()
db = get_db()

@app.on_event("startup")
async def create_tables():
    Base.metadata.create_all(bind=engine)
    
app.include_router(auth_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(history_router, prefix="/api")

# To run the FastAPI app, use the command: uvicorn main:app --reload
