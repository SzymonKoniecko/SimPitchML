"""
src/adapters/api/routers/simulation_router.py
REST Adapter (Controller)
"""

from fastapi import APIRouter, Depends, HTTPException
from src.services import SimulationService
from src.adapters.grpc.client import IterationResultClient, SimulationEngineClient
from src.core import get_logger
from src.adapters.persistence import DatabaseContext

logger = get_logger(__name__)
router = APIRouter()


async def get_sim_engine_grpc_client():
    client = SimulationEngineClient()
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
    iteration_result_client: IterationResultClient = Depends(
        get_iteration_result_grpc_client
    ),
) -> SimulationService:
    return SimulationService(sim_engine_client, iteration_result_client)


@router.get("/simulations/overviews/all")
async def get_simulation_overview(
    service: SimulationService = Depends(get_simulation_service),
):
    logger.info(f"API Request: run_all_overview_scenario())")

    result = await service.run_all_overview_scenario()
    if not result:
        raise HTTPException(
            status_code=404, detail="No simulations found or error occurred"
        )

    return {
        "total_count": result.total_count,
        "items": [
            {
                "id": item.id,
                "created_at": item.created_date,
            }
            for item in result.items
        ],
    }


@router.get("/simulations/iterationresults")
async def get_iteration_results(
    simulation_id: str, service: SimulationService = Depends(get_simulation_service)
):
    logger.info(f"API Request: get_iteration_results(simulation_id={simulation_id})")

    result = await service.run_get_iterationResults_by_simulationId(
        simulation_id=simulation_id
    )

    if not result:
        raise HTTPException(
            status_code=404, detail="No iteration results found or error occurred"
        )
    return {
        "total_count": result.total_count,
        "items": [
            {
                "id": item.id,
                "simulation_id": item.simulation_id,
                "iteration_index": item.iteration_index,
                "start_date": item.start_date,
                "execution_time": item.execution_time,
                "simulated_match_round": item.simulated_match_rounds,
            }
            for item in result.items
        ],
    }


@router.get("/simulations/sync")
async def get_pending_simulations_to_sync(
    service: SimulationService = Depends(get_simulation_service),
):
    result = await service.get_pending_simulations_to_sync()
    
    return [{"id": item} for item in result]
