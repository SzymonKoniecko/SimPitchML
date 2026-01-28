"""
Klient gRPC do serwisu IterationResult
"""
from __future__ import annotations
from typing import Optional
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
        # Upewnij się, że BaseGrpcClient tworzy kanał asynchroniczny (grpc.aio.insecure_channel)
        self.stub = service_pb2_grpc.IterationResultServiceStub(self.channel)

    async def get_all_iterationResults_BySimulationId(
            self, simulation_id: str
        ) -> Optional[PagedResponse[IterationResult]]:
        """
        RPC: GetIterationResultsBySimulationId (Server Streaming)
        """
        try:
            paged_req = commonTypes_pb2.PagedRequestGrpc(
                offset=0,
                limit=5,
                sorting_method=None
            )
            req = requests_pb2.IterationResultsBySimulationIdRequest(
                simulation_id=simulation_id,
                paged_request=paged_req
            )
            
            # W grpc.aio wywołanie metody strumieniującej zwraca obiekt, po którym
            # iterujemy asynchronicznie.
            response_stream = self.stub.GetIterationResultsBySimulationId(req)
            
            all_items = []
            last_paged_info = None

            # UŻYJ async for!
            async for resp in response_stream:
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
                    for o in resp.items
                ]
                all_items.extend(items)
                
                if resp.HasField('paged'):
                    last_paged_info = resp.paged

            if last_paged_info is None:
                return PagedResponse(
                    items=[], 
                    total_count=0, 
                    sorting_option="", 
                    sorting_order=""
                )

            return PagedResponse(
                items=all_items,
                total_count=last_paged_info.total_count,
                sorting_option=last_paged_info.sorting_option,
                sorting_order=last_paged_info.sorting_order,
            )
            
        except grpc.RpcError as e:
            logger.error(f"GetIterationResultsBySimulationId failed: {self._format_rpc_error(e)}")
            return None
