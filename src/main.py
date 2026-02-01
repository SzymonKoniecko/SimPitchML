"""
src/main.py
"""
import uvicorn
from fastapi import FastAPI
from src.adapters.api.routers import simulation_router, sportsdata_router
from src.core.config import config
from src.core.logger import get_logger
import os
from dotenv import load_dotenv

load_dotenv(override=True)
logger = get_logger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(title="SimPitch Client API")
    
    # Rejestracja routerów
    app.include_router(simulation_router.router, prefix="/api/v1", tags=["simulations"])
    app.include_router(sportsdata_router.router, prefix="/api/v1", tags=["sportsData"])
    
    return app

app = create_app()

if __name__ == "__main__":
    logger.info(f"Starting API server")
    uvicorn.run(
        "src.main:app", 
        host=os.getenv("FASTAPI_SEVER_HOST", "0.0.0.0"), 
        port=int(os.getenv("FASTAPI_SEVER_PORT", "8000")), 
        reload=True
    )
