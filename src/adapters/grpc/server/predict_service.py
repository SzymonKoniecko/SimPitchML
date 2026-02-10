# predict_service.py
import grpc
import json
from src.di.ports.simulation_service_port import SimulationServicePort
from src.domain.entities import IterationResult, PredictRequest
from concurrent.futures import ThreadPoolExecutor
from src.generatedSimPitchMlProtos.SimPitchMl.Predict import service_pb2_grpc, requests_pb2, responses_pb2
from src.generatedSimPitchMlProtos.SimPitchMl import commonTypes_pb2

class PredictServiceServicer(service_pb2_grpc.PredictServiceServicer):
    def __init__(self, simulation_service: SimulationServicePort):
        self._simulation_service = simulation_service

    async def StartPrediction(self, request: requests_pb2.PredictRequest, context):
        try:
            grpc_data: commonTypes_pb2.PredictGrpc = request.predict
            
            domain_req = PredictRequest(
                simulation_id=grpc_data.simulation_id,
                league_id=grpc_data.league_id,
                team_strengths=IterationResult.from_team_strength_raw(
                                json.loads(grpc_data.team_strengths)
                            ),
                matches_to_simulate=IterationResult.from_sim_matches_raw(
                                json.loads(grpc_data.matches_to_simulate)
                            ),
                train_until_round_no=grpc_data.train_until_round_no,
                iteration_count=grpc_data.iteration_count,
                league_avg_strength=grpc_data.league_avg_strength or 1.7,
                seed=grpc_data.seed,
                train_ratio=grpc_data.train_ratio or 0.8,
            )
            
            result = await self._simulation_service.run_prediction(predict_request=domain_req)
            
            # domain → proto response
            return responses_pb2.PredictResponse(
                status="COMPLETED",
                predicted_iterations=result
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return responses_pb2.PredictResponse(status="ERROR")