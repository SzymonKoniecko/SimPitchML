from typing import Protocol


class SportsDataServicePort(Protocol):
    async def get_league_rounds_by_league_id(self, league_id: str): ...