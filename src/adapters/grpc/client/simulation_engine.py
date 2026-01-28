"""
src/adapters/grpc/client/simulation.py

Klient gRPC do serwisu SimulationEngine.
"""
from __future__ import annotations
from typing import Optional, AsyncIterator
import grpc

# Zaktualizowane importy
from src.adapters.grpc.client.base import BaseGrpcClient
from src.generated.SimulationEngine import service_pb2_grpc, requests_pb2
from src.generated import commonTypes_pb2
from src.domain.entities import SimulationOverview, PagedResponse
from src.core import get_logger, SimulationGrpcConfig

logger = get_logger(__name__)

class SimulationEngineClient(BaseGrpcClient):
    def __init__(self, grpc_config: Optional[SimulationGrpcConfig] = None):
        super().__init__(grpc_config)
        self.stub = service_pb2_grpc.SimulationEngineServiceStub(self.channel)

    async def get_all_simulation_overviews(
        self, page_number: int = 0, page_size: int = 100
    ) -> Optional[PagedResponse[SimulationOverview]]:
        """
        RPC: GetAllSimulationOverviews
        """
        try:
            req = commonTypes_pb2.PagedRequestGrpc(
                offset=page_number,
                limit=page_size,
                sorting_method=None
            )
            resp = await self.stub.GetAllSimulationOverviews(req)
            
            # Mapowanie proto -> domain entity
            items = [
                SimulationOverview(
                    id=o.id,
                    created_date=o.created_date,
                    league_strengths=o.league_strengths,
                    prior_league_strength=o.prior_league_strength,
                )
                for o in resp.items
            ]

            return PagedResponse(
                items=items,
                total_count=resp.paged.total_count,
                sorting_option=resp.paged.sorting_option,
                sorting_order=resp.paged.sorting_order,
            )
        except grpc.RpcError as e:
            logger.error(f"GetAllSimulationOverviews failed: {self._format_rpc_error(e)}")
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

            if len(page.items) < page_size:
                break
                
            page_number += 1
