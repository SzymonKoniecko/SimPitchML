# src/services/simulation_service.py
from datetime import datetime
from src.core import get_logger
from src.domain.entities import PagedResponse, Synchronization
from src.di.ports.adapters.simulation_engine_port import SimulationEnginePort
from src.di.ports.adapters.iteration_result_port import IterationResultPort
from src.di.ports.synchronization_port import SynchronizationPort

logger = get_logger(__name__)

class SimulationService:
    def __init__(
        self,
        simulation_engine: SimulationEnginePort,
        iteration_results: IterationResultPort,
        synchronization: SynchronizationPort,
    ):
        self._simulation_engine = simulation_engine
        self._iteration_results = iteration_results
        self._synchronization = synchronization

    async def run_all_overview_scenario(self):
        items = []
        async for item in self._simulation_engine.get_all_paged_simulation_overviews():
            items.append(item)

        if not items:
            logger.warning("No items found.")
            return PagedResponse(items=[], total_count=0, sorting_option="", sorting_order="")

        return PagedResponse(
            items=items,
            total_count=len(items),
            sorting_option="",
            sorting_order="",
        )

    async def run_get_iterationResults_by_simulationId(self, simulation_id: str):
        return await self._iteration_results.get_all_iterationResults_BySimulationId(
            simulation_id
        )

    async def get_pending_simulations_to_sync(self):
        synch = self._synchronization.get_synchronization() or Synchronization(
            last_sync_date=datetime(1900, 1, 1),
            added_simulations=0,
        )
        result = await self._simulation_engine.get_latest_simulationIds_by_date(
            latest_date=synch.last_sync_date
        )

        self._synchronization.save_synchronization(
            Synchronization(
                last_sync_date=datetime.now(),
                added_simulations=len(result),
            )
        )

        return result
