from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from src.core import get_logger
from src.di.ports.synchronization_port import SynchronizationPort
from src.domain.entities import PredictRequest
from src.services import SimulationService
from src.di.services import get_simulation_service, get_synchronization_service

logger = get_logger(__name__)
router = APIRouter()


@router.post("/simulations/predict")
async def post_simulation(
    body: PredictRequest = Body(...),
    service: SimulationService = Depends(get_simulation_service),
):
    logger.info(f"API Request POST: post_simulation() with body={body}")

    result = await service.run_prediction(body)

    return {"iterationResults": result}


@router.get("/simulations/overviews/all")
async def get_simulation_overview(
    service: SimulationService = Depends(get_simulation_service),
):
    logger.info("API Request GET: run_all_overview_scenario()")

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
        "API Request GET: get_iteration_results(simulation_id=%s)",
        simulation_id,
    )

    result = await service.run_get_iterationResults_by_simulationId(
        simulation_id=simulation_id
    )

    if not result or not result:
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

#obsolete?
@router.get("/simulations/sync")
async def get_pending_simulations_to_sync(
    service: SimulationService = Depends(get_simulation_service),
):
    logger.info("API Request GET: get_pending_simulations_to_sync()")

    result = await service.get_pending_simulations_to_sync()

    return [{"id": simulation_id} for simulation_id in result]


@router.get("/simulations/sync/list")
async def get_synced_simulations(
    service: SynchronizationPort = Depends(get_synchronization_service),
):
    logger.info("API Request GET: /simulations/sync/list")

    result = service.get_synchronization()

    return {
        "items": [
            {
                "added_simulations": item.added_simulations,
                "last_sync_date": item.last_sync_date,
            }
            for item in result
        ]
    }


@router.delete("/simulations/sync")
async def delete_synced_simulations(
    service: SimulationService = Depends(get_simulation_service),
):
    logger.info("API Request DELETE: /simulations/sync")

    result = (
        await service.delete_simulations_sync_history()
    )  # should return the current state of sync.json

    return {
        "items": [
            {
                "added_simulations": item.added_simulations,
                "last_sync_date": item.last_sync_date,
            }
            for item in result
        ]
    }


@router.delete("/simulations/models")
async def delete_models(
    league_id: str,
    with_meta: Optional[bool] = False,
    service: SimulationService = Depends(get_simulation_service),
):
    logger.info("API Request DELETE: /simulations/models")

    result = await service.delete_models(league_id=league_id, with_meta=with_meta)

    if not result or not result or result == 0:
        raise HTTPException(
            status_code=404,
            detail="Deleted 0 models",
        )

    return {"deleted items": result}


@router.get("/simulations/models")
async def get_models(
    service: SimulationService = Depends(get_simulation_service),
):
    logger.info("API Request GET: /simulations/models")

    result = service.list_all_files("xgboost")

    if not result or not result or result == 0:
        raise HTTPException(
            status_code=404,
            detail="No models found",
        )

    return {"models": result}
