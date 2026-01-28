"""
src/adapters/api/routers/simulation_router.py
REST Adapter (Controller)
"""
from fastapi import APIRouter, Depends, HTTPException
from src.services import SimulationRunnerService
from src.adapters.grpc.client import SimulationEngineClient
from src.core import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Dependency Injection: Fabryka klienta gRPC
async def get_grpc_client():
    # Klient działa jako Context Manager w SimulationRunnerService?
    # W FastAPI lepiej zarządzać cyklem życia przez Depends + yield
    client = SimulationEngineClient()
    try:
        yield client
    finally:
        await client.close()

# Dependency Injection: Fabryka serwisu
def get_simulation_service(client: SimulationEngineClient = Depends(get_grpc_client)) -> SimulationRunnerService:
    return SimulationRunnerService(client)

@router.get("/simulations/overview")
async def get_simulation_overview(
    page_size: int = 5,
    service: SimulationRunnerService = Depends(get_simulation_service)
):
    """
    Endpoint wywołujący logikę z SimulationRunnerService.
    Zwraca JSON zamiast logowania na konsolę.
    """
    logger.info(f"API Request: get_simulation_overview(page_size={page_size})")
    
    # Modyfikujemy serwis, żeby zwracał dane, a nie tylko logował
    # (musimy lekko dostosować SimulationRunnerService, patrz punkt 2)
    result = await service.run_overview_scenario(page_size=page_size)
    
    if not result:
        raise HTTPException(status_code=404, detail="No simulations found or error occurred")
        
    return {
        "total_count": result.total_count,
        "items": [
            {
                "id": item.id,
                "created_at": item.created_date,
                # inne pola...
            }
            for item in result.items
        ]
    }
