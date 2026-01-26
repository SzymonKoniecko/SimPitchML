import asyncio

from src.clients import SimulationEngineClient
from src.utils import config, get_logger

logger = get_logger(__name__)


async def main():
    logger.info("Starting client, target=%s", config.grpc.address)

    async with SimulationEngineClient() as client:
        page = await client.get_all_simulation_overviews(page_number=0, page_size=5)
        if not page:
            logger.error("No response (error or empty).")
            return

        logger.info("Total=%s pages=%s", page.total_count, page.total_pages)
        for item in page.items:
            logger.info("Simulation %s status=%s", item.simulation_id, item.status)


if __name__ == "__main__":
    asyncio.run(main())
