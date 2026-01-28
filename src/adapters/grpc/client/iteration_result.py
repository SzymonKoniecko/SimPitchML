"""
Klient gRPC do serwisu IterationResult
"""
from __future__ import annotations
from typing import Optional, AsyncIterator
import grpc

# Zaktualizowane importy
from src.adapters.grpc.client.base import BaseGrpcClient
from src.generated.IterationResult import service_pb2_grpc, requests_pb2
from src.generated import commonTypes_pb2
from src.domain.entities import IterationResult, PagedResponse
from src.core import get_logger, SimulationGrpcConfig

logger = get_logger(__name__)

class IterationResultClient(BaseGrpcClient):
    def __init__(self, grpc_config: Optional[SimulationGrpcConfig] = None):
        super().__init__(grpc_config)
        self.stub = service_pb2_grpc.IterationResultServiceStub(self.channel)

    async def get_all_iterationResults_BySimulationId(
            self, simulationId
        )-> Optional[PagedResponse[IterationResult]]:
        """
        RPC: GetIterationResultsBySimulationId
        """
        try:
            pagedReq = commonTypes_pb2.PagedRequestGrpc(
                offset=0,
                limit=5,
                sorting_method=None
            )
            req = requests_pb2.IterationResultsBySimulationIdRequest(
                simulation_id=simulationId,
                paged_request=pagedReq
            )
            resp = self.stub.GetIterationResultsBySimulationId(req)
            
            # Mapowanie proto -> domain entity
            items = [
                IterationResult(
                    id=o.id,
                    simulation_id=o.simulation_id,
                    iteration_index=o.iteration_index,
                    start_date=o.start_date,
                    execution_time=o.execution_time,
                    team_strengths=o.team_strengths,
                    simulated_match_rounds=o.simulated_match_rounds,
                )
                for o in resp
            ]

            return PagedResponse(
                items=items,
                total_count=resp.paged.total_count,
                sorting_option=resp.paged.sorting_option,
                sorting_order=resp.paged.sorting_order,
            )
        except grpc.RpcError as e:
            logger.error(f"GetIterationResultsBySimulationId failed: {self._format_rpc_error(e)}")
            return None