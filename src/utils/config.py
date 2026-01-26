from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class GrpcConfig:
    server_host: str = os.getenv("GRPC_SERVER_HOST", "localhost")
    server_port: int = int(os.getenv("GRPC_SERVER_PORT", "40033"))
    timeout_seconds: float = float(os.getenv("GRPC_TIMEOUT", "30"))

    @property
    def address(self) -> str:
        return f"{self.server_host}:{self.server_port}"


@dataclass(frozen=True)
class AppConfig:
    grpc: GrpcConfig = GrpcConfig()


config = AppConfig()
