from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv(override=True)

@dataclass(frozen=True)
class SimulationGrpcConfig:
    server_host: str = os.getenv("SIMULATION_GRPC_SERVER_HOST", "localhost")
    server_port: int = int(os.getenv("SIMULATION_GRPC_SERVER_PORT", "40033"))
    timeout_seconds: float = float(os.getenv("SIMULATION_GRPC_TIMEOUT", "30"))

    @property
    def address(self) -> str:
        return f"{self.server_host}:{self.server_port}"

@dataclass(frozen=True)
class SportsDataGrpcConfig:
    server_host: str = os.getenv("SPORTSDATA_GRPC_SERVER_HOST", "localhost")
    server_port: int = int(os.getenv("SPORTSDATA_GRPC_SERVER_PORT", "40033"))
    timeout_seconds: float = float(os.getenv("SPORTSDATA_GRPC_TIMEOUT", "30"))

    @property
    def address(self) -> str:
        return f"{self.server_host}:{self.server_port}"

@dataclass(frozen=True)
class AppConfig:
    simulation_grpc: SimulationGrpcConfig = field(default_factory=SimulationGrpcConfig)
    sportsdata_grpc: SportsDataGrpcConfig = field(default_factory=SportsDataGrpcConfig)

config = AppConfig()
