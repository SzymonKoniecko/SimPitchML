"""
src/adapters/api/routers/simulation_router.py
REST Adapter (Controller)
"""

from fastapi import APIRouter, Depends, HTTPException
from src.services import SportsDataService
from src.adapters.grpc.client import LeagueRoundClient
from src.core import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def get_league_round_grpc_client():
    client = LeagueRoundClient()
    try:
        yield client
    finally:
        await client.close()


# Dependency Injection: Fabryka serwisu
def get_sportsdata_service(
    league_round_client: LeagueRoundClient = Depends(get_league_round_grpc_client),
) -> SportsDataService:
    return SportsDataService(league_round_client)


@router.get("/sportsdata/leagueRounds")
async def get_league_rounds(
    league_id: str, service: SportsDataService = Depends(get_sportsdata_service)
):

    logger.info(f"API Request: get_league_rounds(league_id={league_id})")

    result = await service.get_league_rounds_by_league_id(league_id=league_id)

    if not result:
        raise HTTPException(
            status_code=404, detail="No league rounds found or error occurred"
        )
    logger.info(type(result))
    return {"items": [r.__dict__ for r in result]}
