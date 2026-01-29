"""
Simulation Runner Service / Use Case
"""
from src.adapters.grpc.client import IterationResultClient, SimulationEngineClient
from src.core import get_logger
from src.domain.entities import PagedResponse

logger = get_logger(__name__)

class SimulationRunnerService:
    def __init__(self, _simulation_engine_client: SimulationEngineClient, _iteration_result_client: IterationResultClient):
        self._simulation_engine_client = _simulation_engine_client
        self._iteration_result_client = _iteration_result_client

    async def run_all_overview_scenario(self):
        all_items = []
        async for item in self._simulation_engine_client.get_all_paged_simulation_overviews():
            all_items.append(item)
        
        if not all_items:
            logger.warning("No items found.")
            return PagedResponse(items=[], total_count=0, sorting_option="", sorting_order="")

        for item in all_items:
            logger.info(f"Simulation {item.id} - created at={item.created_date}")
        
        return PagedResponse(
            items=all_items,
            total_count=len(all_items),
            sorting_option="",
            sorting_order=""
        )
    async def run_paged_overview_scenario(self):
        page = await self._simulation_engine_client.get_all_paged_simulation_overviews()
        
        if not page:
            logger.error("No response (error or empty).")
            return

        for item in page.items:
            logger.info(f"Simulation {item.id} - created at={item.created_date}")
        
        return page
    
    async def run_get_all_iterationResults(self, simulation_id):
        page = await self._iteration_result_client.get_all_iterationResults_BySimulationId(simulation_id)
        
        if not page:
            logger.error("No response (error or empty).")
            return

        logger.info(f"Total iteration results found: {page.total_count}")

        for item in page.items:
            logger.info(f"IterationResult {item.id} - index={item.iteration_index}")
        
        return page
