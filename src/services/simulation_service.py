"""
Application Service / Use Case
"""
from src.adapters.grpc.client import SimulationEngineClient
from src.core import get_logger

logger = get_logger(__name__)

class SimulationRunnerService:
    def __init__(self, client: SimulationEngineClient):
        self.client = client

    async def run_overview_scenario(self, page_size: int = 5):
        page = await self.client.get_all_simulation_overviews(page_number=0, page_size=page_size)
        
        if not page:
            logger.error("No response (error or empty).")
            return

        logger.info(f"Total simulations found: {page.total_count}")

        for item in page.items:
            logger.info(f"Simulation {item.id} - created at={item.created_date}")
