from typing import Optional, List
import grpc
from src.adapters.grpc.client.baseGrpc import BaseGrpcClient
from src.core import get_logger, SportsDataGrpcConfig, config as app_config
from src.di.ports.adapters.match_round_port import MatchRoundPort
from src.domain.entities import MatchRound
from src.generatedSportsDataProtos.SportsDataService.MatchRound import (
    service_pb2_grpc,
    requests_pb2,
)

logger = get_logger(__name__)


class MatchRoundClient(BaseGrpcClient, MatchRoundPort):
    def __init__(self, grpc_config: Optional[SportsDataGrpcConfig] = None):
        super().__init__(grpc_config)
        self.stub = service_pb2_grpc.MatchRoundServiceStub(self.channel)

    async def get_match_rounds_by_round_id(
        self, req_round_id: str
    ) -> List[MatchRound]:
        req = requests_pb2.MatchRoundsByRoundIdRequest(round_id=req_round_id)

        try:
            response = await self.stub.GetMatchRoundsByRoundId(
                req,
                timeout=self.grpc_config.timeout_seconds,
            )  # per-RPC timeout [web:23]
        except grpc.RpcError as e:
            logger.exception(
                "MatchRound RPC failed",
                extra={"grpc": self._format_rpc_error(e)},
            )
            return []

        mapped = [
            MatchRound(
                id=r.id,
                round_id=r.round_id,
                home_team_id=r.home_team_id,
                away_team_id=r.away_team_id,
                home_goals=r.home_goals,
                away_goals=r.away_goals,
                is_draw=r.is_draw,
                is_played=r.is_played,
            )
            for r in response.match_rounds
        ]

        return mapped
