
from typing import List, Protocol, Tuple

from src.domain.entities import PredictRequest, TrainingData, TrainingDataset


class XgboostServicePort(Protocol):
    async def train_evaluate_and_save(self, predictRequest: PredictRequest, t_dataset: TrainingDataset): ...
    async def get_model(self, predictRequest: PredictRequest): ...