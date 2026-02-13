from __future__ import annotations

from typing import Optional, Tuple
from time import perf_counter
from datetime import datetime, timedelta
import uuid
import xgboost as xgb

from src.core.logger import get_logger
from src.domain.entities import (
    InitPrediction,
    IterationResult,
    MatchRound,
    PredictRequest,
    StrengthItem,
    TeamStrength,
    TrainedModels,
    TrainingDataset,
)
from src.domain.features.mapper import Mapper
from src.di.ports.xgboost.xgboost_context_service_port import XgboostContextServicePort
from src.domain.features.trainings.training_builder import TrainingBuilder

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
        logger.info(f" \n CREATED [XGBOOST MODEL] FOR SEED {seed} \n")
        if seed is not None:
            params["random_state"] = seed
        return xgb.XGBRegressor(**params)

    async def train_evaluate_and_save(
        self, predictRequest: PredictRequest, t_dataset: TrainingDataset
    ) -> TrainedModels:

        # 0) Load artifacts (modele + schema)
        artifacts = self._context.load_league_models(league_id=predictRequest.league_id)

        # 1) Schema strategy:
        # - jeśli mamy schema z metadanych, wymuszamy ją już na TRAIN/TEST
        # - jeśli nie mamy (cold start), schema wynika z train i potem ją zapisujemy
        schema = (
            artifacts.feature_schema if artifacts and artifacts.feature_schema else None
        )

        # 2) X/y + schema
        X_train, y_train_home, y_train_away, schema = Mapper.map_to_xy_matrix(
            dataset=t_dataset.train,
            feature_schema=schema,  # None przy cold start, albo wczytana schema
        )
        X_test, y_test_home, y_test_away, _ = Mapper.map_to_xy_matrix(
            dataset=t_dataset.test,
            feature_schema=schema,  # zawsze ta sama schema
        )

        # 3) modele: cold start jeśli brak
        model_home = (
            artifacts.model_home
            if artifacts and artifacts.model_home
            else self._create_model(predictRequest.seed)
        )
        model_away = (
            artifacts.model_away
            if artifacts and artifacts.model_away
            else self._create_model(predictRequest.seed)
        )

        # 4) Fit home/away
        eval_home = [(X_test, y_test_home)] if len(X_test) > 0 else None
        model_home.fit(X_train, y_train_home, eval_set=eval_home, verbose=False)

        eval_away = [(X_test, y_test_away)] if len(X_test) > 0 else None
        model_away.fit(X_train, y_train_away, eval_set=eval_away, verbose=False)

        # 5) Save (modele + schema + opcjonalnie last_overview_created_date)
        self._context.save_league_models(
            league_id=predictRequest.league_id,
            model_home=model_home,
            model_away=model_away,
            feature_schema=schema,
            last_overview_created_date=None,  # w MVP możesz dać None, później ustawisz z SimulationOverview
        )

        return TrainedModels(home=model_home, away=model_away, feature_schema=schema)

    async def get_evaluated_models(
        self, predictRequest: PredictRequest
    ) -> TrainedModels:

        artifacts = self._context.load_league_models(league_id=predictRequest.league_id)

        schema = (
            artifacts.feature_schema if artifacts and artifacts.feature_schema else None
        )

        model_home = (
            artifacts.model_home
            if artifacts and artifacts.model_home
            else self._create_model(predictRequest.seed)
        )
        model_away = (
            artifacts.model_away
            if artifacts and artifacts.model_away
            else self._create_model(predictRequest.seed)
        )

        return TrainedModels(home=model_home, away=model_away, feature_schema=schema)

    async def predict_results(
        self,
        predictRequest: PredictRequest,
        init_prediction: InitPrediction,
        iteration_index: int,
        models: TrainedModels,
    ) -> IterationResult:
        start_execution_time = perf_counter()

        iteration_result = IterationResult(
            id=uuid.uuid4(),
            simulation_id=predictRequest.simulation_id,
            iteration_index=iteration_index,
            start_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            execution_time="",
            team_strengths=[],
            simulated_match_rounds=None,
        )
        iteration_result.simulated_match_rounds = []
        strength_map = TeamStrength.strength_map(predictRequest.team_strengths)
        for match_round in predictRequest.matches_to_simulate:
            prev_round_id = init_prediction.prev_round_id_by_round_id.get(
                match_round.round_id, None
            )
            home_strength = TrainingBuilder.get_strength_or_fallback(
                strength_map,
                init_prediction.round_no_by_round_id,
                match_round.home_team_id,
                prev_round_id,
                league_avg_strength=getattr(predictRequest, "league_avg_strength", 1.7)
            )
            away_strength = TrainingBuilder.get_strength_or_fallback(
                strength_map,
                init_prediction.round_no_by_round_id,
                match_round.away_team_id,
                prev_round_id,
                league_avg_strength=getattr(predictRequest, "league_avg_strength", 1.7)
            )
            predicted_match_round, (predicted_home_ts, predicted_away_ts) = (
                await self.predict_single_result(
                    match_round, home_strength, away_strength, prev_round_id, predictRequest, models
                )
            )
            iteration_result.simulated_match_rounds.append(predicted_match_round)

            strength_map = TeamStrength.add_to_strength_map(
                strength_map, predicted_home_ts
            )
            strength_map = TeamStrength.add_to_strength_map(
                strength_map, predicted_away_ts
            )

        end_execution_time = perf_counter()
        iteration_result.execution_time = str(
            timedelta(seconds=end_execution_time - start_execution_time)
        )

        iteration_result.team_strengths = TeamStrength.strength_map_to_list(
            strength_map
        )
        return iteration_result

    async def predict_single_result(
        self,
        match_round: MatchRound,
        home_strength: Optional[TeamStrength],
        away_strength: Optional[TeamStrength],
        prev_round_id: str,
        predictRequest: PredictRequest,
        models: TrainedModels,
    ) -> Tuple[MatchRound, Tuple[TeamStrength, TeamStrength]]:
        """
        Predykuje wynik pojedynczego MatchRound i zwraca wypełniony obiekt + nowe TeamStrength.

        Args:
            match_round: Pusty MatchRound (is_played=False).
            models: Wytrenowane modele + schema.
            prev_round_id: Snapshot TeamStrength PRZED tym meczem.
            league_avg_strength: Fallback TeamStrength (jeśli brak danych o drużynie).

        Returns:
            (wypełniony MatchRound, (home_strength_updated, away_strength_updated))
        """

        x_row = TrainingBuilder.build_single_training_data(
            match_round=match_round,
            home_strength=home_strength,
            away_strength=away_strength,
            prev_round_id=prev_round_id,
        )

        x_predict = Mapper.map_to_x_matrix([x_row], models.feature_schema)

        pred_home_goals = float(models.home.predict(x_predict)[0])
        pred_away_goals = float(models.away.predict(x_predict)[0])

        # Post-process (clamp + round)
        MAX_GOALS = 15
        pred_home_goals = max(0.0, min(float(MAX_GOALS), pred_home_goals))
        pred_away_goals = max(0.0, min(float(MAX_GOALS), pred_away_goals))

        home_goals = int(round(pred_home_goals))
        away_goals = int(round(pred_away_goals))

        match_round.home_goals = home_goals
        match_round.away_goals = away_goals
        match_round.is_draw = home_goals == away_goals
        match_round.is_played = True

        team_strength_home = home_strength.SetLikelihood()
        team_strength_home.SetPosterior(games_to_reach_trust=predictRequest.games_to_reach_trust, league_strength=predictRequest.league_avg_strength)
        team_strength_home.SetExpectedGoalsFromPosterior()

        team_strength_away = away_strength.SetLikelihood()
        team_strength_away.SetPosterior(games_to_reach_trust=predictRequest.games_to_reach_trust, league_strength=predictRequest.league_avg_strength)
        team_strength_away.SetExpectedGoalsFromPosterior()

        return match_round, (team_strength_home, team_strength_away)
