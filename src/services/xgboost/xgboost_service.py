from typing import List, Tuple
from src.di.ports.xgboost.xgboost_context_service_port import XgboostContextServicePort
from src.domain.entities import PredictRequest, TrainingData, TrainingDataset
from src.domain.features.trainings import training_builder, training_split
import xgboost as xgb
import pandas as pd

class XgboostService:
    def __init__(self, context: XgboostContextServicePort):
        self._context = context

    async def train_evaluate_and_save(self, predictRequest: PredictRequest, t_dataset: TrainingDataset):
        model = self.get_model(predictRequest)
        return 

    async def get_model(self, predictRequest: PredictRequest):
        return await self._context.load_league_model(predictRequest.league_id)