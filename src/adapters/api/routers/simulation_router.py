from fastapi import APIRouter, Depends, HTTPException
from src.core import get_logger
from src.services.simulation_service import SimulationService
from src.di import get_simulation_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("/simulations/overviews/all")
async def get_simulation_overview(
    service: SimulationService = Depends(get_simulation_service),
):
    logger.info("API Request: run_all_overview_scenario()")

    result = await service.run_all_overview_scenario()

    if not result or not result.items:
        raise HTTPException(
            status_code=404,
            detail="No simulations found or error occurred",
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
    simulation_id: str,
    service: SimulationService = Depends(get_simulation_service),
):
    logger.info(
        "API Request: get_iteration_results(simulation_id=%s)",
        simulation_id,
    )

    result = await service.run_get_iterationResults_by_simulationId(
        simulation_id=simulation_id
    )

    if not result or not result.items:
        raise HTTPException(
            status_code=404,
            detail="No iteration results found or error occurred",
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
    logger.info("API Request: get_pending_simulations_to_sync()")

    result = await service.get_pending_simulations_to_sync()

    return [{"id": simulation_id} for simulation_id in result]
