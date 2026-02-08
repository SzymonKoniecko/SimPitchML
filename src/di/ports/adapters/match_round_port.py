from typing import List, Protocol

from src.domain.entities import MatchRound


class MatchRoundPort(Protocol):
    async def get_match_rounds_by_round_id(
        self, req_round_id: str
    ) -> List[MatchRound]: ...
