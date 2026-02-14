# src/services/simulation_service.py
from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional, Tuple
from src.core import get_logger
from src.di.ports.adapters.league_round_port import LeagueRoundPort
from src.di.ports.sportsdata_service_port import SportsDataServicePort
from src.di.ports.xgboost.xgboost_service_port import XgboostServicePort
from src.domain.entities import (
    InitPrediction,
    IterationResult,
    LeagueRound,
    PagedResponse,
    PredictRequest,
    Synchronization,
    TrainedModels,
    TrainingData,
    TrainingDataset,
)
from src.di.ports.adapters.simulation_engine_port import SimulationEnginePort
from src.di.ports.adapters.iteration_result_port import IterationResultPort
from src.di.ports.synchronization_port import SynchronizationPort
from src.domain.features.mapper import Mapper
from src.domain.features.trainings.training_builder import TrainingBuilder
from src.domain.features.trainings.training_split import TrainingSplit

logger = get_logger(__name__)


class SimulationService:
    def __init__(
        self,
        simulation_engine: SimulationEnginePort,
        iteration_results: IterationResultPort,
        synchronization: SynchronizationPort,
        sportsdata_service: SportsDataServicePort,
        xgboost_service: XgboostServicePort,
    ):
        self._simulation_engine = simulation_engine
        self._iteration_results = iteration_results
        self._synchronization = synchronization
        self._sportsdata_service = sportsdata_service
        self._xgboost_service = xgboost_service

    async def run_prediction_stream(
        self, predict_request: PredictRequest
    ) -> AsyncIterator[Tuple[str, Optional[IterationResult], int]]:
        try:
            models: TrainedModels = None
            rounds = await self._sportsdata_service.get_league_rounds_by_league_id(
                league_id=predict_request.league_id
            )
            prev_round_id_by_round_id: Dict[str, str] = (
                Mapper.map_prev_round_id_by_round_id(
                    Mapper.map_round_no_by_round_id(rounds)
                )
            )

            init_prediction = await self.init_prediction(
                predict_request, rounds, prev_round_id_by_round_id
            )

            if init_prediction.list_simulation_ids:
                models = await self._xgboost_service.train_evaluate_and_save(
                    predictRequest=predict_request,
                    t_dataset=init_prediction.training_dataset,
                )
            else:
                models = await self._xgboost_service.get_evaluated_models(
                    predict_request
                )

            counter = 0

            for iteration in range(predict_request.iteration_count):
                iteration_result = await self._xgboost_service.predict_results(
                    predict_request, init_prediction, iteration, models
                )
                counter += 1

                # stream item
                yield ("RUNNING", iteration_result, counter)
        except Exception:
            logger.exception("Yield/mapper crashed")
            raise

        # final event as last yield (instead of return value)
        yield ("COMPLETED", None, counter)

    async def init_prediction(
        self,
        predict_request: PredictRequest,
        rounds: List[LeagueRound],
        prev_round_id_by_round_id: Dict[str, str],
    ) -> InitPrediction:

        list_simulation_ids = await self.get_pending_simulations_to_sync()
        if predict_request.simulation_id in list_simulation_ids:
            list_simulation_ids.remove(
                predict_request.simulation_id
            )  # do not use currently proceeded simulation

        all_match_rounds = (
            await self._sportsdata_service.get_match_rounds_by_league_rounds(rounds)
        )
        list_training_data_dataset = []

        round_no_by_round_id = Mapper.map_round_no_by_round_id(rounds)
        round_id_by_round_no = Mapper.map_round_id_by_round_no(rounds)

        if list_simulation_ids is not None and len(list_simulation_ids) != 0:
            for sim_id in list_simulation_ids:
                paged_iteration_results = (
                    await self.run_get_iterationResults_by_simulationId(
                        simulation_id=sim_id
                    )
                )
                for it_result in paged_iteration_results.items:
                    tmp_dataset = TrainingBuilder.build_dataset(
                        iteration_result=it_result,
                        match_rounds=await self._sportsdata_service.concat_match_rounds_by_simulated_match_rounds(
                            all_match_rounds=all_match_rounds,
                            simulated_match_rounds=it_result.simulated_match_rounds,
                        ),
                        prev_round_id_by_round_id=prev_round_id_by_round_id,
                        round_no_by_round_id=round_no_by_round_id,
                        round_id_by_round_no=round_id_by_round_no,
                        league_id=predict_request.league_id,
                        league_avg=predict_request.league_avg_strength,
                    )
                    list_training_data_dataset.extend(  # extend() because of stays in the single list
                        tmp_dataset
                    )
        training_splitted_dataset = TrainingSplit.define_train_split(
            dataset=list_training_data_dataset,
            round_no_by_round_id=round_no_by_round_id,
            train_until_round_no=predict_request.train_until_round_no,
            train_ratio=predict_request.train_ratio,
        )

        return InitPrediction(
            training_splitted_dataset,
            list_simulation_ids,
            prev_round_id_by_round_id,
            round_no_by_round_id,
            round_id_by_round_no,
        )

    async def run_all_overview_scenario(self):
        items = []
        async for item in self._simulation_engine.get_all_paged_simulation_overviews():
            items.append(item)

        if not items:
            logger.warning("No items found.")
            return PagedResponse(
                items=[], total_count=0, sorting_option="", sorting_order=""
            )

        return PagedResponse(
            items=items,
            total_count=len(items),
            sorting_option="",
            sorting_order="",
        )

    async def run_get_iterationResults_by_simulationId(
        self, simulation_id: str
    ) -> Optional[PagedResponse[IterationResult]]:
        result: Optional[PagedResponse[IterationResult]] = (
            await self._iteration_results.get_all_iterationResults_BySimulationId(
                simulation_id
            )
        )
        return result

    async def get_pending_simulations_to_sync(self) -> List[str]:
        synch = self._synchronization.get_synchronization() or Synchronization(
            last_sync_date=datetime(1900, 1, 1),
            added_simulations=0,
        )
        result = await self._simulation_engine.get_latest_simulationIds_by_date(
            latest_date=synch.last_sync_date
        )

        self._synchronization.save_synchronization(
            Synchronization(
                last_sync_date=datetime.now(),
                added_simulations=len(result),
            )
        )

        return result
