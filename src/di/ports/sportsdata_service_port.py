from typing import List, Protocol

from src.domain.entities import LeagueRound, MatchRound


class SportsDataServicePort(Protocol):
    async def get_league_rounds_by_league_id(self, league_id: str): ...
    async def get_match_rounds_by_league_rounds(
        self, league_rounds: List[LeagueRound]
    ) -> List[MatchRound]: ...
    async def concat_match_rounds_by_simulated_match_rounds(
        self,
        all_match_rounds: List[MatchRound],
        simulated_match_rounds: List[MatchRound],
    ) -> List[MatchRound]: ...
