import uvicorn
import grpc
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
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

raw_IS_RELOAD = os.getenv("IS_RELOAD", "False").strip()
if raw_IS_RELOAD not in ("True", "False"):
    raise ValueError(f"IS_RELOAD must be True/False, got {raw_IS_RELOAD!r}")
IS_RELOAD = (raw_IS_RELOAD == "True")

grpc_server: grpc.Server = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global grpc_server

    server = grpc.server(ThreadPoolExecutor(max_workers=10))

    predict_servicer = get_predict_grpc_servicer()
    service_pb2_grpc.add_PredictServiceServicer_to_server(predict_servicer, server)

    server.add_insecure_port(f"[::]:{GRPC_PORT}")

    SERVICE_NAMES = (
        service_pb2.DESCRIPTOR.services_by_name["PredictService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)  # reflection pattern [web:130]

    server.start()
    grpc_server = server
    logger.info(f"gRPC started on :{GRPC_PORT}")

    yield

    grpc_server.stop(0)
    grpc_server.wait_for_termination(timeout=5)
    logger.info("gRPC stopped")

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
