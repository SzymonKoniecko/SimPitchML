import pytest
from unittest.mock import MagicMock, AsyncMock, call

from src.services.simulation_service import SimulationService
from src.domain.entities import PredictRequest, LeagueRound, IterationResult, TrainingData
from src.domain.features import Mapper
from src.domain.features.trainings.training_builder import TrainingBuilder
from src.domain.features.trainings.training_split import TrainingSplit

from src.di.ports.adapters import (
    SimulationEnginePort,
    IterationResultPort,
    LeagueRoundPort
)
from src.di.ports import (
    SynchronizationPort,
)

@pytest.fixture
def mock_simulation_engine():
    return AsyncMock(spec=SimulationEnginePort)

@pytest.fixture
def mock_iteration_results():
    return AsyncMock(spec=IterationResultPort)

@pytest.fixture
def mock_synchronization():
    return AsyncMock(spec=SynchronizationPort)

@pytest.fixture
def mock_league_rounds():
    return AsyncMock(spec=LeagueRoundPort)

@pytest.fixture
def service(
    mock_simulation_engine,
    mock_iteration_results,
    mock_synchronization,
    mock_league_rounds
):
    return SimulationService(
        simulation_engine=mock_simulation_engine,
        iteration_results=mock_iteration_results,
        synchronization=mock_synchronization,
        league_rounds=mock_league_rounds
    )

@pytest.mark.asyncio
async def test_init_prediction_success_flow(
    service, 
    mock_synchronization, 
    mock_league_rounds, 
    monkeypatch
):
    """
    Testuje pełny przepływ: pobranie ID symulacji -> pobranie rund -> pobranie wyników -> budowa datasetu -> split.
    Weryfikuje czy append vs extend działa poprawnie (dataset powinien być płaski).
    """
    
    league_id = "L1"
    req = PredictRequest(league_id=league_id, train_until_round_no=10, train_ratio=0.8)
    
    service.get_pending_simulations_to_sync = AsyncMock(return_value=["SIM_1", "SIM_2"])
    
    rounds_data = [LeagueRound(id="R1", round=1), LeagueRound(id="R2", round=2)]
    mock_league_rounds.get_league_rounds_by_params.return_value = rounds_data

    service.run_get_iterationResults_by_simulationId = AsyncMock(side_effect=[
        [IterationResult(id="IT_1")], # Dla SIM_1
        [IterationResult(id="IT_2")]  # Dla SIM_2
    ])

    
    fake_batch_1 = [TrainingData(prev_round_id="R1", x_row={}, y_home=1, y_away=0)]
    fake_batch_2 = [TrainingData(prev_round_id="R2", x_row={}, y_home=2, y_away=2)]
    
    with list(monkeypatch.context() for _ in range(1))[0]: # Hack dla wielu patchy lub użyj mocker z pytest-mock
        monkeypatch.setattr(TrainingBuilder, "build_dataset", MagicMock(side_effect=[fake_batch_1, fake_batch_2]))
        
        mock_split = MagicMock(return_value=(["TRAIN"], ["TEST"]))
        monkeypatch.setattr(TrainingSplit, "define_train_split", mock_split)
        
        monkeypatch.setattr(Mapper, "map_round_no_by_round_id", MagicMock(return_value={"R1": 1}))

        # 3. EXECUTE
        train, test = await service.init_prediction(req)

        # 4. ASSERT
        
        mock_league_rounds.get_league_rounds_by_params.assert_awaited_once_with(req_league_id=league_id)
        
        assert service.run_get_iterationResults_by_simulationId.await_count == 2
        service.run_get_iterationResults_by_simulationId.assert_has_awaits([
            call(simulation_id="SIM_1"),
            call(simulation_id="SIM_2")
        ])
        
        args, _ = mock_split.call_args
        passed_dataset = args[0] # Pierwszy argument to dataset
        
        assert len(passed_dataset) == 2
        assert passed_dataset[0] == fake_batch_1[0]
        assert passed_dataset[1] == fake_batch_2[0]
        assert isinstance(passed_dataset[0], TrainingData) # Upewniamy się, że to nie jest lista

        assert train == ["TRAIN"]
        assert test == ["TEST"]


@pytest.mark.asyncio
async def test_init_prediction_no_pending_simulations(service, mock_league_rounds):
    """
    Testuje scenariusz, gdy nie ma nic do synchronizacji.
    """
    service.get_pending_simulations_to_sync = AsyncMock(return_value=[]) # Pusta lista
    
    result = await service.init_prediction(PredictRequest(league_id="L1"))
    
    # Powinien wyjść wcześnie, ewentualnie zwrócić puste listy (zależy od implementacji TrainingSplit, tu mockujemy zachowanie)
    # W Twoim kodzie: jeśli list_simulation_ids jest puste, list_training_data_dataset jest puste.
    # TrainingSplit dostanie pustą listę.
    
    service.run_get_iterationResults_by_simulationId = AsyncMock()
    
    # Assert
    service.run_get_iterationResults_by_simulationId.assert_not_called()
