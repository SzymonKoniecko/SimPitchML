"""
src/adapters/api/routers/simulation_router.py
REST Adapter (Controller)
"""
from fastapi import APIRouter, Depends, HTTPException
from src.services import SimulationRunnerService
from src.adapters.grpc.client import IterationResultClient, SimulationEngineClient
from src.core import get_logger

logger = get_logger(__name__)
router = APIRouter()

async def get_sim_engine_grpc_client():
    client = IterationResultClient()
    try:
        yield client
    finally:
        await client.close()
async def get_iteration_result_grpc_client():
    client = IterationResultClient()
    try:
        yield client
    finally:
        await client.close()

# Dependency Injection: Fabryka serwisu
def get_simulation_service(
        sim_engine_client: SimulationEngineClient = Depends(get_sim_engine_grpc_client),
        iteration_result_client: IterationResultClient = Depends(get_iteration_result_grpc_client)
) -> SimulationRunnerService:
    return SimulationRunnerService(sim_engine_client, iteration_result_client)

@router.get("/simulations/overview")
async def get_simulation_overview(
    page_size: int = 5,
    service: SimulationRunnerService = Depends(get_simulation_service)
):
    logger.info(f"API Request: get_simulation_overview(page_size={page_size})")
    
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
@router.get("/simulations/iterationresults")
async def get_iteration_results(
    page_size: int = 5,
    service: SimulationRunnerService = Depends(get_simulation_service)
):
    logger.info(f"API Request: run_get_all_iterationResults()")
    
    result = await service.run_get_all_iterationResults()
    
    if not result:
        raise HTTPException(status_code=404, detail="No iterationresults found or error occurred")
        
    return {
        "total_count": result.total_count,
        "items": [
            {
                "id": item.id,
                "index": item.iteration_index,
            }
            for item in result.items
        ]
    }