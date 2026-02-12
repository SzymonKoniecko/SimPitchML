import json
import grpc
from src.core.logger import get_logger
from src.di.ports.simulation_service_port import SimulationServicePort
from src.domain.entities import PredictRequest, IterationResult
from src.domain.features.mapper import Mapper
from src.generatedSimPitchMlProtos.SimPitchMl.Predict import service_pb2_grpc, requests_pb2
from src.generatedSimPitchMlProtos.SimPitchMl import commonTypes_pb2

logger = get_logger(__name__)

class PredictServiceServicer(service_pb2_grpc.PredictServiceServicer):
    def __init__(self, simulation_service: SimulationServicePort):
        self._simulation_service = simulation_service

    async def StreamPrediction(self, request: requests_pb2.PredictRequest, context: grpc.aio.ServicerContext):
        grpc_data: commonTypes_pb2.PredictGrpc = request.predict

        domain_req = PredictRequest(
            simulation_id=grpc_data.simulation_id,
            league_id=grpc_data.league_id,
            team_strengths=IterationResult.from_team_strength_raw_new(json.loads(grpc_data.team_strengths or "[]")),
            matches_to_simulate=IterationResult.from_sim_matches_raw_new(json.loads(grpc_data.matches_to_simulate or "[]")),
            train_until_round_no=grpc_data.train_until_round_no,
            iteration_count=grpc_data.iteration_count,
            league_avg_strength=getattr(grpc_data, "league_avg_strength"),
            seed=getattr(grpc_data, "seed"),
            train_ratio=getattr(grpc_data, "train_ratio"),
        )

        async for status, iteration_result, counter in self._simulation_service.run_prediction_stream(domain_req):
            if context.cancelled():
                logger.info("Stream cancelled for simulation_id=%s", domain_req.simulation_id)
                return

            yield Mapper.map_to_predict_response(
                status=status,
                iteration_result=iteration_result,
                counter=counter,
            )
