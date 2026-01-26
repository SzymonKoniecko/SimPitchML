import asyncio

from src.clients import SimulationEngineClient
from src.utils import config, get_logger
from src.models import PagedResponse
logger = get_logger(__name__)


async def main():
    logger.info("Starting client, target=%s", config.grpc.address)

    async with SimulationEngineClient() as client:
        page = await client.get_all_simulation_overviews(page_number=0, page_size=5)
        if not page:
            logger.error("No response (error or empty).")
            return

        logger.info("Total={page.total_count} pages={page.sorting_option}")
        for item in page.items:
            logger.info("Simulation {item.id} - created at={item.created_date}")


if __name__ == "__main__":
    asyncio.run(main())
