from datetime import datetime
from typing import List, Optional, Protocol, AsyncIterator, Union
from src.domain.entities import PagedResponse, SimulationOverview


class SimulationEnginePort(Protocol):
    async def get_paged_simulation_overviews(
        self, offset: int, limit: int
    ) -> Optional[PagedResponse[SimulationOverview]]: ...

    async def get_all_paged_simulation_overviews(
        self,
    ) -> AsyncIterator[SimulationOverview]: ...

    async def get_latest_simulationIds_by_date(
        self, latest_date: Union[str, datetime]
    ) -> List[str]: ...
