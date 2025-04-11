from fastapi import FastAPI
from routers.auth import router as auth_router
from routers.analysis import router as analysis_router
from routers.history import router as history_router

app = FastAPI()

app.include_router(analysis_router, prefix="/api/analyze")
app.include_router(auth_router, prefix="/api/auth")
app.include_router(history_router, prefix="/api/history")

# To run the FastAPI app, use the command: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)