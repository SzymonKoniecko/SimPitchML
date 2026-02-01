"""
Klient gRPC do serwisu IterationResult
"""
from __future__ import annotations
from typing import Optional
import os
import grpc
import json
from src.adapters.grpc.client.baseGrpc import BaseGrpcClient
from src.generatedSimulationProtos.SimulationService.IterationResult import service_pb2_grpc, requests_pb2
from src.generatedSimulationProtos.SimulationService import commonTypes_pb2
from src.domain.entities import IterationResult, PagedResponse
from src.core import get_logger, SimulationGrpcConfig

logger = get_logger(__name__)

try:
    BATCH_LIMIT = int(os.getenv("GRPC_PAGINATION_LIMIT", "100"))
except ValueError:
    BATCH_LIMIT = 100

class IterationResultClient(BaseGrpcClient):
    def __init__(self, grpc_config: Optional[SimulationGrpcConfig] = None):
        super().__init__(grpc_config)
        self.stub = service_pb2_grpc.IterationResultServiceStub(self.channel)

    async def get_all_iterationResults_BySimulationId(
            self, simulation_id: str
        ) -> Optional[PagedResponse[IterationResult]]:
        all_items = []
        current_offset = 0
        final_total_count = 0
        final_sorting_option = ""
        final_sorting_order = ""
        
        try:
            while True:
                paged_req = commonTypes_pb2.PagedRequestGrpc(
                    offset=current_offset,
                    limit=BATCH_LIMIT,
                    sorting_method=None
                )
                
                req = requests_pb2.IterationResultsBySimulationIdRequest(
                    simulation_id=simulation_id,
                    paged_request=paged_req
                )
                
                response_stream = self.stub.GetIterationResultsBySimulationId(req)
                
                items_in_this_batch = 0
                batch_paged_info = None

                async for resp in response_stream:
                    mapped_items = [
                        IterationResult(
                            id=o.id,
                            simulation_id=o.simulation_id,
                            iteration_index=o.iteration_index,
                            start_date=o.start_date,
                            execution_time=o.execution_time,
                            team_strengths=IterationResult.from_team_strength_raw(json.loads(o.team_strengths)),
                            simulated_match_rounds=IterationResult.from_sim_matches_raw(json.loads(o.simulated_match_rounds)),
                        )
                        for o in resp.items
                    ]
                    all_items.extend(mapped_items)
                    items_in_this_batch += len(mapped_items)
                    
                    if resp.HasField('paged'):
                        batch_paged_info = resp.paged

                # Aktualizacja metadanych z ostatniej paczki
                if batch_paged_info:
                    final_total_count = batch_paged_info.total_count
                    final_sorting_option = batch_paged_info.sorting_option
                    final_sorting_order = batch_paged_info.sorting_order

                if items_in_this_batch < BATCH_LIMIT:
                    break
                
                current_offset += BATCH_LIMIT
                
                if final_total_count > 0 and len(all_items) >= final_total_count:
                    break
            
            return PagedResponse(
                items=all_items,
                total_count=final_total_count, # lub len(all_items)
                sorting_option=final_sorting_option,
                sorting_order=final_sorting_order,
            )

        except grpc.RpcError as e:
            logger.error(f"GetIterationResultsBySimulationId failed: {self._format_rpc_error(e)}")
            return None
