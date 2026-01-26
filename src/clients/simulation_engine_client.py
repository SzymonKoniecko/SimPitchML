"""
src/clients/simulation_client.py

Klient do SimulationEngineService.
Zakładamy, że wygenerowane pliki są w: src/generated/...
"""

from __future__ import annotations

from typing import Optional, AsyncIterator

import grpc

from src.clients.base_client import BaseGrpcClient
from src.generated.SimulationEngine import service_pb2_grpc, requests_pb2
from src.generated import commonTypes_pb2

from src.models import SimulationOverview, PagedResponse
from src.utils import get_logger
from src.utils.config import GrpcConfig

logger = get_logger(__name__)


class SimulationEngineClient(BaseGrpcClient):
    def __init__(self, grpc_config: Optional[GrpcConfig] = None):
        super().__init__(grpc_config)
        self.stub = service_pb2_grpc.SimulationEngineServiceStub(self.channel)

    async def get_all_simulation_overviews(
        self, page_number: int = 0, page_size: int = 10
    ) -> Optional[PagedResponse[SimulationOverview]]:
        """
        RPC: GetAllSimulationOverviews(PagedRequestGrpc) -> SimulationOverviewsPagedResponse
        """
        try:
            req = commonTypes_pb2.PagedRequestGrpc(
                page_number=page_number,
                page_size=page_size,
            )
            resp = await self.stub.GetAllSimulationOverviews(req)

            items = [
                SimulationOverview(
                    id=o.id,
                    created_date=o.created_date,
                    league_strengths=o.league_strengths,
                    prior_league_strength=o.prior_league_strength,
                )
                for o in resp.overviews
            ]

            return PagedResponse(
                items=items,
                total_count=resp.total_count,
                sorting_option=resp.sorting_option,
                sorting_order=resp.sorting_order,
            )
        except grpc.RpcError as e:
            logger.error("GetAllSimulationOverviews failed: %s", self._format_rpc_error(e))
            return None

    async def iter_all_simulation_overviews(
        self, page_size: int = 50
    ) -> AsyncIterator[SimulationOverview]:
        """
        Helper: iteruje po wszystkich stronach (auto-paginacja).
        """
        page_number = 0
        while True:
            page = await self.get_all_simulation_overviews(page_number, page_size)
            if not page or not page.items:
                break

            for item in page.items:
                yield item

            if page_number >= page.total_pages - 1:
                break
            page_number += 1
