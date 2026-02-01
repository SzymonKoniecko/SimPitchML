from src.adapters.grpc.client import league_round
from src.core import get_logger
from src.domain.entities import LeagueRound

logger = get_logger(__name__)


class SportsDataService:
    def __init__(self, league_round_client: league_round.LeagueRoundClient):
        self._league_round_client = league_round_client

    async def get_league_rounds_by_league_id(self, league_id: str):
        result = await self._league_round_client.get_league_rounds_by_params(
            req_league_id=league_id
        )

        return result
