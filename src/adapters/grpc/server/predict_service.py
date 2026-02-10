# predict_service.py
import asyncio
import json
import grpc

from src.di.ports.simulation_service_port import SimulationServicePort
from src.domain.entities import PredictRequest, IterationResult
from src.generatedSimPitchMlProtos.SimPitchMl.Predict import service_pb2_grpc, requests_pb2, responses_pb2
from src.generatedSimPitchMlProtos.SimPitchMl import commonTypes_pb2
from src.core.logger import get_logger

logger = get_logger(__name__)

class PredictServiceServicer(service_pb2_grpc.PredictServiceServicer):
    def __init__(self, simulation_service: SimulationServicePort):
        self._simulation_service = simulation_service
        self._tasks: dict[str, asyncio.Task] = {}  # opcjonalnie: trzymanie referencji per simulation_id

    async def StartPrediction(self, request: requests_pb2.PredictRequest, context: grpc.aio.ServicerContext):
        try:
            grpc_data: commonTypes_pb2.PredictGrpc = request.predict

            domain_req = PredictRequest(
                simulation_id=grpc_data.simulation_id,
                league_id=grpc_data.league_id,
                team_strengths=IterationResult.from_team_strength_raw(json.loads(grpc_data.team_strengths or "[]")),
                matches_to_simulate=IterationResult.from_sim_matches_raw(json.loads(grpc_data.matches_to_simulate or "[]")),
                train_until_round_no=grpc_data.train_until_round_no,
                iteration_count=grpc_data.iteration_count,
                league_avg_strength=getattr(grpc_data, "league_avg_strength", 1.7),
                seed=getattr(grpc_data, "seed", None),
                train_ratio=getattr(grpc_data, "train_ratio", 0.8),
            )

            simulation_id = domain_req.simulation_id

            # background job
            task = asyncio.create_task(self._run_prediction_job(domain_req))
            self._tasks[simulation_id] = task

            # (opcjonalnie) sprzątanie kiedy RPC się zakończy; add_done_callback istnieje w grpc.aio
            context.add_done_callback(lambda _call: None)

            return responses_pb2.PredictResponse(status="RUNNING")

        except Exception as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return responses_pb2.PredictResponse(status="ERROR")

    async def _run_prediction_job(self, domain_req: PredictRequest):
        try:
            result = await self._simulation_service.run_prediction(domain_req)
            logger.info("Prediction completed for simulation_id=%s, predicted_iterations=%s",
                        domain_req.simulation_id, len(result))
        except Exception:
            logger.exception("Prediction failed for simulation_id=%s", domain_req.simulation_id)
        finally:
            self._tasks.pop(domain_req.simulation_id, None)
