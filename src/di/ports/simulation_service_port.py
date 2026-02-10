from typing import Dict, List, Optional, Protocol, Tuple

from src.domain.entities import (
    InitPrediction,
    IterationResult,
    LeagueRound,
    PredictRequest,
    TrainingData,
    TrainingDataset,
)


class SimulationServicePort(Protocol):
    async def run_prediction(
        self, predict_request: PredictRequest
    ) -> List[IterationResult]: ...
    async def init_prediction(
        self,
        predict_request: PredictRequest,
        rounds: List[LeagueRound],
        prev_round_id_by_round_id: Dict[str, str],
    ) -> InitPrediction: ...
    async def run_all_overview_scenario(self): ...
    async def run_get_iterationResults_by_simulationId(
        self,
    ) -> Optional[IterationResult]: ...
    async def get_pending_simulations_to_sync(self) -> List[str]: ...
