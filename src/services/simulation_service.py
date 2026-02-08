# src/services/simulation_service.py
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from src.core import get_logger
from src.di.ports.adapters.league_round_port import LeagueRoundPort
from src.di.ports.sportsdata_service_port import SportsDataServicePort
from src.di.ports.xgboost.xgboost_service_port import XgboostServicePort
from src.domain.entities import (
    IterationResult,
    PagedResponse,
    PredictRequest,
    Synchronization,
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

    async def run_prediction(self, predict_request: PredictRequest):
        full_training_dataset = await self.init_prediction(
            predict_request=predict_request
        )
        return await self._xgboost_service.train_evaluate_and_save(
            predict_request, full_training_dataset
        )

    async def init_prediction(self, predict_request: PredictRequest) -> TrainingDataset:

        list_simulation_ids = await self.get_pending_simulations_to_sync()
        rounds = await self._sportsdata_service.get_league_rounds_by_league_id(
            league_id=predict_request.league_id
        )
        all_match_rounds = (
            await self._sportsdata_service.get_match_rounds_by_league_rounds(rounds)
        )
        # list_iteration_results = []
        list_training_data_dataset = []

        if list_simulation_ids is not None and len(list_simulation_ids) != 0:
            for sim_id in list_simulation_ids:
                iteration_results = await self.run_get_iterationResults_by_simulationId(
                    simulation_id=sim_id
                )
                for it_result in iteration_results:
                    tmp_dataset = TrainingBuilder.build_dataset(
                        iteration_result=it_result,
                        league_rounds=rounds,
                        match_rounds=await self._sportsdata_service.concat_match_rounds_by_simulated_match_rounds(
                            all_match_rounds=all_match_rounds,
                            simulated_match_rounds=it_result.simulated_match_rounds,
                        ),
                    )
                    list_training_data_dataset.extend(  # stays in the single list
                        tmp_dataset
                    )

        return TrainingSplit.define_train_split(
            dataset=list_training_data_dataset,
            round_no_by_round_id=Mapper.map_round_no_by_round_id(rounds),
            train_until_round_no=predict_request.train_until_round_no,
            train_ratio=predict_request.train_ratio,
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
    ) -> Optional[IterationResult]:
        result: Optional[PagedResponse[IterationResult]] = (
            await self._iteration_results.get_all_iterationResults_BySimulationId(
                simulation_id
            )
        )
        return result.items

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
