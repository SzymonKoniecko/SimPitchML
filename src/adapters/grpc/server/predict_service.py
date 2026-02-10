# predict_service.py
import grpc
import json
import asyncio
from src.di.ports.simulation_service_port import SimulationServicePort
from src.domain.entities import PredictRequest, IterationResult
from src.generatedSimPitchMlProtos.SimPitchMl.Predict import service_pb2_grpc, requests_pb2, responses_pb2
from src.generatedSimPitchMlProtos.SimPitchMl import commonTypes_pb2

class PredictServiceServicer(service_pb2_grpc.PredictServiceServicer):
    def __init__(self, simulation_service: SimulationServicePort):
        self._simulation_service = simulation_service

    def StartPrediction(self, request: requests_pb2.PredictRequest, context):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            grpc_data: commonTypes_pb2.PredictGrpc = request.predict
            
            domain_req = PredictRequest(
                simulation_id=grpc_data.simulation_id,
                league_id=grpc_data.league_id,
                team_strengths=IterationResult.from_team_strength_raw(json.loads(grpc_data.team_strengths or "[]")),
                matches_to_simulate=IterationResult.from_sim_matches_raw(json.loads(grpc_data.matches_to_simulate or "[]")),
                train_until_round_no=grpc_data.train_until_round_no,
                iteration_count=grpc_data.iteration_count,
                league_avg_strength=getattr(grpc_data, 'league_avg_strength', 1.7),
                seed=getattr(grpc_data, 'seed', None),
                train_ratio=getattr(grpc_data, 'train_ratio', 0.8),
            )
            
            result = loop.run_until_complete(self._simulation_service.run_prediction(domain_req))
            
            return responses_pb2.PredictResponse(
                status="COMPLETED",
                predicted_iterations=result
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return responses_pb2.PredictResponse(status="ERROR")
        finally:
            loop.close()
