from __future__ import annotations

from typing import Optional

import xgboost as xgb

from src.core.logger import get_logger
from src.domain.entities import PredictRequest, TrainedModels, TrainingDataset
from src.domain.features.mapper import Mapper
from src.di.ports.xgboost.xgboost_context_service_port import XgboostContextServicePort

logger = get_logger(__name__)

BASE_PARAMS = {
    "n_estimators": 100,
    "max_depth": 3,
    "learning_rate": 0.1,
    "objective": "count:poisson",
    "n_jobs": -1,
}

class XgboostService:
    def __init__(self, context: XgboostContextServicePort):
        self._context = context

    def _create_model(self, seed: Optional[int]) -> xgb.XGBRegressor:
        params = dict(BASE_PARAMS)
        if seed is not None:
            params["random_state"] = seed
        return xgb.XGBRegressor(**params)

    async def train_evaluate_and_save(
        self,
        predictRequest: PredictRequest,
        t_dataset: TrainingDataset
    ) -> TrainedModels:

        # 1) X/y + schema (train wyznacza schema)
        X_train, y_train_home, y_train_away, schema = Mapper.map_to_xy_matrix(
            dataset=t_dataset.train,
            feature_schema=None,
        )
        X_test, y_test_home, y_test_away, _ = Mapper.map_to_xy_matrix(
            dataset=t_dataset.test,
            feature_schema=schema,
        )

        # 2) Load lub cold-start DWÓCH modeli
        # (na start możesz zawsze cold-start; poniżej wersja mieszana)
        loaded = await self._context.load_league_models(predictRequest.league_id)
        if loaded is None:
            model_home = self._create_model(predictRequest.seed)
            model_away = self._create_model(predictRequest.seed)
        else:
            model_home, model_away = loaded

        # 3) Fit home
        eval_home = [(X_test, y_test_home)] if len(X_test) > 0 else None
        model_home.fit(X_train, y_train_home, eval_set=eval_home, verbose=False)

        # 4) Fit away
        eval_away = [(X_test, y_test_away)] if len(X_test) > 0 else None
        model_away.fit(X_train, y_train_away, eval_set=eval_away, verbose=False)

        # 5) Save dwa modele + schema (krok 6)
        await self._context.save_league_models(
            league_id=predictRequest.league_id,
            model_home=model_home,
            model_away=model_away,
            feature_schema=schema,
        )

        return TrainedModels(home=model_home, away=model_away, feature_schema=schema)
