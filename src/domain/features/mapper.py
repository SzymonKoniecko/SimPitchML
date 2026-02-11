from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from src.domain.entities import IterationResult, LeagueRound, TrainingData
from src.generatedSimulationProtos.SimulationService import (
    commonTypes_pb2 as commonTypes_SimulationService,
)
from src.generatedSimPitchMlProtos.SimPitchMl.Predict import responses_pb2 as responses_pb2_SimPitchMl

GUID_EMPTY = "00000000-0000-0000-0000-000000000000"


class Mapper:
    def __init__(self):
        pass

    @staticmethod
    def map_round_no_by_round_id(rounds: List[LeagueRound]) -> Dict[str, int]:
        rounds_sorted = sorted(rounds, key=lambda x: x.round, reverse=False)
        return {r.id: r.round for r in rounds_sorted}

    @staticmethod
    def map_prev_round_id_by_round_id(rounds: Dict[str, int]) -> Dict[str, str]:
        """
        Input:  {"r2":2,"r3":3}
        Output: {"r2":"r1","r3":"r2"} (prev round id for each round id)

        *Risk if roundId is null* Currently its Guid.Empty
        """

        id_by_no: Dict[int, str] = {
            round_no: round_id for round_id, round_no in rounds.items()
        }

        prev_by_id: Dict[str, str] = {}

        for round_id, round_no in rounds.items():
            prev_round_id = id_by_no.get(round_no - 1, GUID_EMPTY)
            prev_by_id[round_id] = prev_round_id

        return prev_by_id

    @staticmethod
    def map_to_xy_matrix(
        dataset: List[TrainingData],
        feature_schema: Optional[List[str]] = None,
        fill_value: float = 0.0,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series, List[str]]:
        """
        Konwertuje List[TrainingData] -> (X, y_home, y_away, feature_schema).

        - Jeśli feature_schema jest None: bierze kolumny z DataFrame i zwraca je jako schema.
        - Jeśli feature_schema jest podane: dopasowuje DataFrame do tej listy kolumn
        (brakujące kolumny uzupełnia fill_value, nadmiarowe usuwa).
        Zwracane schema zawsze odpowiada kolumnom w X (kolejność ma znaczenie przy predict).
        """
        if not dataset:
            empty_X = pd.DataFrame(columns=feature_schema or [])
            return (
                empty_X,
                pd.Series(dtype=int),
                pd.Series(dtype=int),
                (feature_schema or []),
            )

        rows = [item.x_row for item in dataset]
        X = pd.DataFrame(rows)  # list-of-dicts -> DataFrame

        if feature_schema is None:
            feature_schema = list(X.columns)

        # Wymuszamy identyczne kolumny i kolejność (ważne dla train/predict)
        X = X.reindex(columns=feature_schema, fill_value=fill_value)

        y_home = pd.Series([item.y_home for item in dataset], dtype=int)
        y_away = pd.Series([item.y_away for item in dataset], dtype=int)

        return X, y_home, y_away, feature_schema

    @staticmethod
    def extract_feature_schema(dataset: List["TrainingData"]) -> List[str]:
        """
        Wyciąga listę cech (kolumn) z datasetu.
        Przydatne, jeśli chcesz zapisać schema do JSON i później użyć w predykcji.
        """
        if not dataset:
            return []
        return list(pd.DataFrame([d.x_row for d in dataset]).columns)

    @staticmethod
    def map_to_x_matrix(
        x_rows: List[dict[str, Any]],
        feature_schema: List[str],
        fill_value: float = 0.0,
    ) -> pd.DataFrame:
        X = pd.DataFrame(x_rows)
        # wymuś kolumny i kolejność (braki uzupełnij)
        return X.reindex(columns=feature_schema, fill_value=fill_value)

    @staticmethod
    def map_iteration_result_to_proto(
        iteration_result: IterationResult,
    ) -> commonTypes_SimulationService.IterationResultGrpc:
        grpc_object = commonTypes_SimulationService.IterationResultGrpc(
            id=iteration_result.id,
            simulation_id=iteration_result.simulation_id,
            # iteration_index = iteration_result.iteration_index, SimulationService will add proper one
            start_date=iteration_result.start_date,
            execution_time=iteration_result.execution_time,
            team_strengths=IterationResult.team_strengths_to_json_value(
                iteration_result.team_strengths
            ),
            simulated_match_rounds=IterationResult.simulated_match_rounds_to_json_value(
                iteration_result.simulated_match_rounds
            ),
        )
        return grpc_object

    @staticmethod
    def map_to_predict_response(
        status: str, iteration_result, counter: int
    ) -> responses_pb2_SimPitchMl.PredictResponse:
        grpc_obj = responses_pb2_SimPitchMl.PredictResponse(
            status=status,
            predicted_iterations=counter,
            iteration_result=Mapper.map_iteration_result_to_proto(iteration_result),
        )
        return grpc_obj
