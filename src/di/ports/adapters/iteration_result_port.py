from typing import Optional, Protocol

from src.domain.entities import IterationResult, PagedResponse


class IterationResultPort(Protocol):
    async def get_all_iterationResults_BySimulationId(
        self, simulation_id: str
    ) -> Optional[PagedResponse[IterationResult]]: ...
    async def send_iteration_result(
        self, iteration_result: IterationResult
    ) -> bool: ...
