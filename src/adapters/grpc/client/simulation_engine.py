"""
Klient gRPC do serwisu SimulationEngine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, AsyncIterator, List, Union
import os
import grpc

from src.adapters.grpc.client.baseGrpc import BaseGrpcClient
from src.core import get_logger, SimulationGrpcConfig, config as app_config
from src.domain.entities import SimulationOverview, PagedResponse
from src.generatedSimulationProtos.SimulationService import commonTypes_pb2
from src.generatedSimulationProtos.SimulationService.SimulationEngine import (
    service_pb2_grpc,
    requests_pb2,
)

logger = get_logger(__name__)

try:
    BATCH_LIMIT = int(os.getenv("GRPC_PAGINATION_LIMIT", "100"))
except ValueError:
    BATCH_LIMIT = 100


class SimulationEngineClient(BaseGrpcClient):
    def __init__(self, grpc_config: Optional[SimulationGrpcConfig] = None):
        super().__init__(grpc_config or app_config.simulation_grpc)
        self.stub = service_pb2_grpc.SimulationEngineServiceStub(self.channel)

    async def get_paged_simulation_overviews(
        self, offset: int = 0, limit: int = 100
    ) -> Optional[PagedResponse[SimulationOverview]]:
        try:
            req = commonTypes_pb2.PagedRequestGrpc(
                offset=offset,
                limit=limit,
                sorting_method=None,
            )

            resp = await self.stub.GetAllSimulationOverviews(
                req,
                timeout=self.grpc_config.timeout_seconds,
            )  # timeout per-call [web:18]

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
            logger.exception(
                "GetAllSimulationOverviews failed",
                extra={"grpc": self._format_rpc_error(e)},
            )
            return None

    async def get_all_paged_simulation_overviews(self) -> AsyncIterator[SimulationOverview]:
        current_offset = 0

        while True:
            page = await self.get_paged_simulation_overviews(
                offset=current_offset,
                limit=BATCH_LIMIT,
            )

            if not page or not page.items:
                logger.warning("No simulation overviews or empty page.items.")
                break

            for item in page.items:
                yield item

            if len(page.items) < BATCH_LIMIT:
                break

            current_offset += BATCH_LIMIT

    async def get_latest_simulationIds_by_date(
        self, latest_date: Union[str, datetime]
    ) -> List[str]:
        if isinstance(latest_date, datetime):
            formatted_date_str = latest_date.isoformat(timespec="milliseconds")
        elif isinstance(latest_date, str):
            formatted_date_str = latest_date
        else:
            raise TypeError(
                f"Invalid type for latest_date: {type(latest_date)}. Expected str or datetime."
            )

        request = requests_pb2.GetLatestSimulationIdsRequest(date=formatted_date_str)

        try:
            result = await self.stub.GetLatestSimulationIds(
                request,
                timeout=self.grpc_config.timeout_seconds,
            )  # timeout per-call [web:18]
        except grpc.RpcError as e:
            logger.exception(
                "GetLatestSimulationIds failed",
                extra={"grpc": self._format_rpc_error(e)},
            )
            return []

        return list(result.simulation_ids)
