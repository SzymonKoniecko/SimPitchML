from src.adapters.grpc.server.predict_service import PredictServiceServicer
import uvicorn
import grpc
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import AsyncExitStack, asynccontextmanager
from src.adapters.api.routers import simulation_router, sportsdata_router
from src.core.config import config
from src.core.logger import get_logger
from src.core.logger import get_logger
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from src.di.services import get_predict_grpc_servicer
from grpc_reflection.v1alpha import reflection

# Twoje generated proto
try:
    from src.generatedSimPitchMlProtos.SimPitchMl.Predict import requests_pb2, responses_pb2, service_pb2_grpc, service_pb2
    from src.generatedSimPitchMlProtos.SimPitchMl import commonTypes_pb2
except ImportError:
    print("gRPC proto missing. Run: make proto-simpitch")
    exit(1)

load_dotenv(override=True)
logger = get_logger(__name__)

FASTAPI_PORT = int(os.getenv("SIMPITCHML_SERVICE_CONTAINER_PORT_REST", "4006"))
GRPC_PORT = int(os.getenv("SIMPITCHML_SERVICE_CONTAINER_PORT_GRPC", "40066"))

#logger.info(f'{int(os.getenv("SIMPITCHML_SERVICE_HOST_PORT_REST", "4006"))} // {int(os.getenv("SIMPITCHML_SERVICE_HOST_PORT_GRPC", "4006"))} // {int(os.getenv("SIMPITCHML_SERVICE_CONTAINER_PORT_REST", "4006"))} // {int(os.getenv("SIMPITCHML_SERVICE_CONTAINER_PORT_GRPC", "4006"))} // ')


raw_IS_RELOAD = os.getenv("IS_RELOAD", "False").strip()
if raw_IS_RELOAD not in ("True", "False"):
    raise ValueError(f"IS_RELOAD must be True/False, got {raw_IS_RELOAD!r}")
IS_RELOAD = (raw_IS_RELOAD == "True")

grpc_server: grpc.Server = None

logger = get_logger(__name__)

from src.di.services import (
    get_sim_engine_client,
    get_iteration_result_client,
    get_league_round_client,
    get_match_round_client,
    get_json_repo,
    get_synchronization_service,
    get_xgboost_context_service,
    get_xgboost_service,
    get_sportsdata_service,
    get_simulation_service,
)

async def _anext(agen):
    return await agen.__anext__()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        # resolve async-generator deps (te z yield)
        engine_agen = get_sim_engine_client()
        engine = await _anext(engine_agen)
        stack.push_async_callback(engine_agen.aclose)

        iter_agen = get_iteration_result_client()
        iteration_results = await _anext(iter_agen)
        stack.push_async_callback(iter_agen.aclose)

        league_agen = get_league_round_client()
        league_round = await _anext(league_agen)
        stack.push_async_callback(league_agen.aclose)

        match_agen = get_match_round_client()
        match_round = await _anext(match_agen)
        stack.push_async_callback(match_agen.aclose)

        # resolve sync deps
        repo = get_json_repo()
        synchronization = get_synchronization_service(repo=repo)
        xgb_context = get_xgboost_context_service(repo=repo)
        xgboost_service = get_xgboost_service(context=xgb_context)
        sportsdata_service = get_sportsdata_service(league_round=league_round, match_round=match_round)

        # IMPORTANT: to jest TA SAMA instancja SimulationService z Twojego factory
        simulation_service = get_simulation_service(
            engine=engine,
            iteration_results=iteration_results,
            synchronization=synchronization,
            sportsdata_service=sportsdata_service,
            xgboost_service=xgboost_service,
        )

        # gRPC aio server (dla stream)
        server = grpc.aio.server()
        servicer = PredictServiceServicer(simulation_service)
        service_pb2_grpc.add_PredictServiceServicer_to_server(servicer, server)

        server.add_insecure_port(f"[::]:{GRPC_PORT}")

        SERVICE_NAMES = (
            service_pb2.DESCRIPTOR.services_by_name["PredictService"].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(SERVICE_NAMES, server)

        await server.start()
        app.state.grpc_server = server

        yield

        await server.stop(0)

def create_app() -> FastAPI:
    app = FastAPI(title="SimPitch ML Service", lifespan=lifespan)
    app.include_router(simulation_router.router, prefix="/api/v1", tags=["simulations"])
    app.include_router(sportsdata_router.router, prefix="/api/v1", tags=["sportsData"])
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "grpc_port": GRPC_PORT}
    
    return app

app = create_app()

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

if __name__ == "__main__":
    logger.info(f"SimPitch ML REST:{FASTAPI_PORT} gRPC:{GRPC_PORT}")
    uvicorn.run("src.main:app", host="0.0.0.0", port=FASTAPI_PORT, reload=IS_RELOAD)
