from fastapi import Depends
from src.services.simulation_service import SimulationService
from src.adapters.grpc.client import SimulationEngineClient, IterationResultClient
from src.adapters.persistence.json_repository import JsonFileRepository
from src.services.sportsdata_service import SportsDataService
from src.services.synchronization_service import SynchronizationService

async def get_sim_engine_client():
    client = SimulationEngineClient()
    try:
        yield client
    finally:
        await client.close()

async def get_iteration_result_client():
    client = IterationResultClient()
    try:
        yield client
    finally:
        await client.close()

async def get_league_round_client():
    client = IterationResultClient()
    try:
        yield client
    finally:
        await client.close()

def get_json_repo():
    return JsonFileRepository()

def get_synchronization_service(
    repo = Depends(get_json_repo),
):
    return SynchronizationService(repo)

def get_simulation_service(
    engine = Depends(get_sim_engine_client),
    iteration_results = Depends(get_iteration_result_client),
    synchronization = Depends(get_synchronization_service),
):
    return SimulationService(engine, iteration_results, synchronization)

def get_sportsdata_service(
    league_round = Depends(get_league_round_client)
): 
    return SportsDataService(league_round_client=league_round)