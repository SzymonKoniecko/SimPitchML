from __future__ import annotations

from typing import Optional, Protocol
import grpc

from src.core import get_logger, config as app_config, SimulationGrpcConfig, SportsDataGrpcConfig

logger = get_logger(__name__)

class GrpcConfig(Protocol):
    address: str
    timeout_seconds: float
#test mergeeee vscode
class BaseGrpcClient:
    def __init__(self, grpc_config: Optional[GrpcConfig] = None):
        self.grpc_config: GrpcConfig = grpc_config or app_config.simulation_grpc
        self.channel: grpc.aio.Channel = self._create_channel()

    def _create_channel(self) -> grpc.aio.Channel:
        address = self.grpc_config.address
        logger.info(f"Connecting to gRPC server: {address}")
        return grpc.aio.insecure_channel(address)

    async def close(self) -> None:
        await self.channel.close()

    def _format_rpc_error(self, e: grpc.RpcError) -> dict:
        return {"code": str(e.code()), "details": e.details()}

    async def __aenter__(self) -> "BaseGrpcClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
