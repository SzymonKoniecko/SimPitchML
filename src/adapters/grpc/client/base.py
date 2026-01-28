
from __future__ import annotations
from typing import Optional
import grpc
from src.core import get_logger, SimulationGrpcConfig, config as app_config

logger = get_logger(__name__)

class BaseGrpcClient:
    def __init__(self, grpc_config: Optional[SimulationGrpcConfig] = None):
        self.grpc_config = grpc_config or app_config.grpc
        self.channel: grpc.aio.Channel = self._create_channel()

    def _create_channel(self) -> grpc.aio.Channel:
        # Dev: insecure. Produkcja: secure_channel + credentials.
        address = self.grpc_config.address
        logger.info(f"Connecting to gRPC server: {address}")
        return grpc.aio.insecure_channel(address)

    async def close(self) -> None:
        await self.channel.close()

    def _format_rpc_error(self, e: grpc.RpcError) -> dict:
        return {
            "code": str(e.code()),
            "details": e.details(),
        }

    async def __aenter__(self) -> "BaseGrpcClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
