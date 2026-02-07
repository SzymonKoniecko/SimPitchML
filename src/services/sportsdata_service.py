from typing import List
from src.adapters.grpc.client import league_round, match_round
from src.core import get_logger
from src.di.ports.sportsdata_service_port import SportsDataServicePort
from src.domain.entities import LeagueRound, MatchRound

logger = get_logger(__name__)


class SportsDataService(SportsDataServicePort):
    def __init__(
        self,
        league_round_client: league_round.LeagueRoundClient,
        match_round_client: match_round.MatchRoundClient,
    ):
        self._league_round_client = league_round_client
        self._match_rounds_client = match_round_client

    async def get_league_rounds_by_league_id(self, league_id: str):
        result = await self._league_round_client.get_league_rounds_by_params(
            req_league_id=league_id
        )

        return result

    async def get_match_rounds_by_league_rounds(
        self, league_rounds: List[LeagueRound]
    ) -> List[MatchRound]:
        match_rounds: List[MatchRound] = []

        for round in league_rounds:
            match_rounds.extend(
                await self._match_rounds_client.get_match_rounds_by_round_id(
                    req_round_id=round.id
                )
            )
        return match_rounds

    async def concat_match_rounds_by_simulated_match_rounds(
        self,
        all_match_rounds: List["MatchRound"],
        simulated_match_rounds: List["MatchRound"],
    ) -> List["MatchRound"]:
        simulated_ids = {m.id for m in simulated_match_rounds}

        merged = [m for m in all_match_rounds if m.id not in simulated_ids]
        merged.extend(simulated_match_rounds)
        return merged