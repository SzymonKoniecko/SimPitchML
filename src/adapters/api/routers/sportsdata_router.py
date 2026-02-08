"""
src/adapters/api/routers/simulation_router.py
REST Adapter (Controller)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from src.services import SportsDataService
from src.adapters.grpc.client import LeagueRoundClient
from src.core import get_logger
from src.di.services import get_sportsdata_service

logger = get_logger(__name__)
router = APIRouter()


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
    return {"items": [r.__dict__ for r in result]}

@router.get("/sportsdata/matchRounds")
async def get_match_rounds(
    league_id: str, service: SportsDataService = Depends(get_sportsdata_service)
):

    logger.info(f"API Request: get_match_rounds(league_id={league_id})")

    league_rounds = await service.get_league_rounds_by_league_id(league_id=league_id)
    result = await service.get_match_rounds_by_league_rounds(league_rounds)
    if not result:
        raise HTTPException(
            status_code=404, detail="No match rounds found or error occurred"
        )
    return {"items": [r.__dict__ for r in result]}