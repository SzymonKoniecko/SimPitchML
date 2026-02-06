
from typing import List, Protocol, Tuple

from src.domain.entities import PredictRequest, TrainingData


class XgboostServicePort(Protocol):
    async def train_evaluate_and_save(self, predictRequest: PredictRequest, splitted_dataset: Tuple[List[TrainingData], List[TrainingData]]): ...
    async def get_model(self, predictRequest: PredictRequest): ...