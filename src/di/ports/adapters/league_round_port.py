from typing import List, Protocol

from src.domain.entities import LeagueRound


class LeagueRoundPort(Protocol):
    async def get_league_rounds_by_params(
        self, req_league_id: str
    ) -> List[LeagueRound]: ...