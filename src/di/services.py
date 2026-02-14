from fastapi import Depends
from src.adapters.grpc.client.iteration_result import IterationResultClient
from src.adapters.grpc.client.league_round import LeagueRoundClient
from src.adapters.grpc.client.match_round import MatchRoundClient
from src.adapters.grpc.client.simulation_engine import SimulationEngineClient
from src.adapters.grpc.server.predict_service import PredictServiceServicer
from src.adapters.persistence.json_repository import JsonFileRepository
from src.di.ports.simulation_service_port import SimulationServicePort
from src.domain.entities import PredictRequest
from src.services.simulation_service import SimulationService
from src.services.sportsdata_service import SportsDataService
from src.services.synchronization_service import SynchronizationService
from src.services.xgboost.xgboost_context_service import XgBoostContextService
from src.services.xgboost.xgboost_service import XgboostService


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
    client = LeagueRoundClient()
    try:
        yield client
    finally:
        await client.close()


async def get_match_round_client():
    client = MatchRoundClient()
    try:
        yield client
    finally:
        await client.close()


def get_json_repo():
    return JsonFileRepository()


def get_synchronization_service(
    repo=Depends(get_json_repo),
):
    return SynchronizationService(repo)


def get_xgboost_context_service(
    repo=Depends(get_json_repo),
):
    return XgBoostContextService(repo)


def get_xgboost_service(context=Depends(get_xgboost_context_service)):
    return XgboostService(context)


def get_sportsdata_service(
    league_round=Depends(get_league_round_client),
    match_round=Depends(get_match_round_client),
):
    return SportsDataService(
        league_round_client=league_round, match_round_client=match_round
    )


def get_simulation_service(
    engine=Depends(get_sim_engine_client),
    iteration_results=Depends(get_iteration_result_client),
    synchronization=Depends(get_synchronization_service),
    sportsdata_service=Depends(get_sportsdata_service),
    xgboost_service=Depends(get_xgboost_service),
):
    return SimulationService(
        engine, iteration_results, synchronization, sportsdata_service, xgboost_service
    )

def get_predict_grpc_servicer(
    simulation_service: SimulationServicePort = Depends(get_simulation_service),
) -> PredictServiceServicer:
    """
    DI: tworzy gRPC servicer na bazie już istniejącego SimulationService (port).
    NIE tworzymy nowego SimulationService - korzystamy z get_simulation_service().
    """
    return PredictServiceServicer(simulation_service)