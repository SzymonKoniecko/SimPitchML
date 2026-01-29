"""
Klient gRPC do serwisu SimulationEngine.
"""
from __future__ import annotations
from typing import Optional, AsyncIterator
import os
import grpc

# Zaktualizowane importy
from src.adapters.grpc.client.base import BaseGrpcClient
from src.generated.SimulationEngine import service_pb2_grpc, requests_pb2
from src.generated import commonTypes_pb2
from src.domain.entities import SimulationOverview, PagedResponse
from src.core import get_logger, SimulationGrpcConfig

logger = get_logger(__name__)

try:
    BATCH_LIMIT = int(os.getenv("GRPC_PAGINATION_LIMIT", "100"))
except ValueError:
    BATCH_LIMIT = 100

class SimulationEngineClient(BaseGrpcClient):
    def __init__(self, grpc_config: Optional[SimulationGrpcConfig] = None):
        super().__init__(grpc_config)
        self.stub = service_pb2_grpc.SimulationEngineServiceStub(self.channel)

    async def get_paged_simulation_overviews(
        self, offset: int = 0, limit: int = 100
    ) -> Optional[PagedResponse[SimulationOverview]]:
        """
        RPC: GetAllSimulationOverviews
        Pobiera jedną stronę wyników.
        """
        try:
            req = commonTypes_pb2.PagedRequestGrpc(
                offset=offset,
                limit=limit,
                sorting_method=None
            )
            
            resp = await self.stub.GetAllSimulationOverviews(req)
            
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

    async def get_all_paged_simulation_overviews(
        self
    ) -> AsyncIterator[SimulationOverview]:
        """
        Helper: iteruje po WSZYSTKICH wynikach (auto-paginacja).
        Pobiera dane strona po stronie i zwraca je jako pojedynczy strumień (generator).
        """
        current_offset = 0
        
        while True:
            page = await self.get_paged_simulation_overviews(
                offset=current_offset, 
                limit=BATCH_LIMIT
            )
            print(current_offset)
            if not page or not page.items:
                logger.warning("not simulation_overviews or not *.items")
                break

            for item in page.items:
                yield item

            if len(page.items) < BATCH_LIMIT:
                break
                
            current_offset += BATCH_LIMIT
        