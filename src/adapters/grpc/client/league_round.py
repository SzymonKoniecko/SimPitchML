from __future__ import annotations

from typing import Optional, List
import grpc

from src.adapters.grpc.client.baseGrpc import BaseGrpcClient
from src.core import get_logger, SportsDataGrpcConfig, config as app_config
from src.generatedSportsDataProtos.SportsDataService.LeagueRound import (
    service_pb2_grpc,
    requests_pb2,
)
from src.domain.entities import LeagueRound
from src.di.ports.adapters.league_round_port import LeagueRoundPort

logger = get_logger(__name__)


class LeagueRoundClient(BaseGrpcClient, LeagueRoundPort):
    def __init__(self, grpc_config: Optional[SportsDataGrpcConfig] = None):
        super().__init__(grpc_config or app_config.sportsdata_grpc)
        self.stub = service_pb2_grpc.LeagueRoundServiceStub(self.channel)

    async def get_league_rounds_by_params(self, req_league_id: str) -> List[LeagueRound]:
        request = requests_pb2.LeagueRoundsByParamsRequest(league_id=req_league_id)

        try:
            response = await self.stub.GetAllLeagueRoundsByParams(
                request,
                timeout=self.grpc_config.timeout_seconds,
            )
        except grpc.RpcError as e:
            logger.exception(
                "LeagueRound RPC failed",
                extra={"grpc": self._format_rpc_error(e)},
            )
            return []

        mapped = [
            LeagueRound(
                id=r.id,
                league_id=r.league_id,
                season_year=r.season_year,
                round=r.round,
            )
            for r in response.league_rounds
        ]


        return mapped
