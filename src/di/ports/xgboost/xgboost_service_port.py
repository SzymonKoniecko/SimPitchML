from typing import List, Optional, Protocol, Tuple

from src.domain.entities import (
    InitPrediction,
    IterationResult,
    MatchRound,
    PredictRequest,
    TeamStrength,
    TrainedModels,
    TrainingData,
    TrainingDataset,
)


class XgboostServicePort(Protocol):
    async def train_evaluate_and_save(
        self, predictRequest: PredictRequest, t_dataset: TrainingDataset
    ) -> TrainedModels: ...
    async def get_evaluated_models(
        self, predictRequest: PredictRequest
    ) -> TrainedModels: ...
    async def get_model(self, predictRequest: PredictRequest): ...
    async def predict_results(
        self,
        predictRequest: PredictRequest,
        init_prediction: InitPrediction,
        iteration_index: int,
        models: TrainedModels,
    ) -> IterationResult: ...
    async def predict_single_result(
        self,
        match_round: MatchRound,
        home_strength: Optional[TeamStrength],
        away_strength: Optional[TeamStrength],
        prev_round_id: str,
        predictRequest: PredictRequest,
        models: TrainedModels,
    ) -> Tuple[MatchRound, Tuple[TeamStrength, TeamStrength]]: ...
