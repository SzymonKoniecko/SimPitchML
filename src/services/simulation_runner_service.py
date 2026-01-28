"""
Application Service / Use Case
"""
from src.adapters.grpc.client import IterationResultClient, SimulationEngineClient
from src.core import get_logger

logger = get_logger(__name__)

class SimulationRunnerService:
    def __init__(self, _simulation_engine_client: SimulationEngineClient, _iteration_result_client: IterationResultClient):
        self._simulation_engine_client = _simulation_engine_client
        self._iteration_result_client = _iteration_result_client

    async def run_overview_scenario(self, page_size: int = 5):
        page = await self._simulation_engine_client.get_paged_simulation_overviews(page_number=0, page_size=page_size)
        
        if not page:
            logger.error("No response (error or empty).")
            return

        logger.info(f"Total simulations found: {page.total_count}")

        for item in page.items:
            logger.info(f"Simulation {item.id} - created at={item.created_date}")
        
        return page
    
    async def run_get_all_iterationResults(self):
        page = await self._iteration_result_client.get_all_iterationResults_BySimulationId("747f1fa1-8bd8-4107-9911-63abfbea4aac")
        
        if not page:
            logger.error("No response (error or empty).")
            return

        logger.info(f"Total iteration results found: {page.total_count}")

        for item in page.items:
            logger.info(f"IterationResult {item.id} - index={item.iteration_index}")
        
        return page
