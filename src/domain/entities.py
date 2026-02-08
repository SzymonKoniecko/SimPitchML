from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Generic, Iterable, Optional, Tuple, TypeVar, List, Union
import json

import pandas as pd

T = TypeVar("T")

from src.core import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SimulationOverview:
    id: str
    created_date: str
    league_strengths: str
    prior_league_strength: float


@dataclass(frozen=True)
class IterationResult:
    id: str
    simulation_id: str
    iteration_index: int
    start_date: str
    execution_time: str
    team_strengths: List[TeamStrength]
    simulated_match_rounds: List[MatchRound]

    @staticmethod
    def from_team_strength_raw(data: Union[str, List[Dict]]) -> List[TeamStrength]:
        if data is None:
            return []

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                logger.error(
                    f"Failed to decode TeamStrength JSON: {data[:100]}..."
                )  # Log snippet only
                return []

        return [
            TeamStrength(
                team_id=item.get("TeamId") or item.get("team_id"),
                likelihood=StrengthItem(
                    offensive=item["Likelihood"]["Offensive"],
                    defensive=item["Likelihood"]["Defensive"],
                ),
                posterior=StrengthItem(
                    offensive=item["Posterior"]["Offensive"],
                    defensive=item["Posterior"]["Defensive"],
                ),
                expected_goals=str(
                    item.get("ExpectedGoals", 0.0)
                ),  # Safe access + string conversion
                last_update=item["LastUpdate"],
                round_id=item.get("RoundId") or item.get("round_id"),
            )
            for item in data
        ]

    @staticmethod
    def from_sim_matches_raw(data: Union[str, List[Dict]]) -> List[MatchRound]:
        if data is None:
            return []

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return []

        return [
            MatchRound(
                id=item.get("Id") or item.get("id"),
                round_id=item.get("RoundId") or item.get("round_id"),
                home_team_id=item.get("HomeTeamId") or item.get("home_team_id"),
                away_team_id=item.get("AwayTeamId") or item.get("away_team_id"),
                home_goals=item.get("HomeGoals", 0),
                away_goals=item.get("AwayGoals", 0),
                is_draw=item.get("IsDraw", False),
                is_played=item.get("IsPlayed", True),
            )
            for item in data
        ]

    def to_pretty_string(self) -> str:
        import dataclasses
        import json

        data_dict = dataclasses.asdict(self)

        return json.dumps(data_dict, indent=4, default=str)


@dataclass(frozen=True)
class MatchRound:
    id: str
    round_id: str
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int
    is_draw: bool
    is_played: bool


@dataclass(frozen=True)
class LeagueRound:
    id: str
    league_id: str
    season_year: str
    round: int


@dataclass(frozen=True)
class StrengthItem:
    offensive: float
    defensive: float


@dataclass(frozen=False)
class TeamStrength:
    team_id: str
    likelihood: StrengthItem
    posterior: StrengthItem
    expected_goals: str
    last_update: str
    round_id: str
    # season_stats: int

    @staticmethod
    def strength_map(
        items: Iterable["TeamStrength"],
    ) -> Dict[Tuple[str, str], "TeamStrength"]:
        return {(ts.team_id, ts.round_id): ts for ts in items}
    
    @staticmethod
    def league_average_baseline(
        *,
        round_id: str = "LEAGUE_AVG",
        last_update: str = "2001-01-01T22:00:00.000000",
        expected_goals: str = "N/A",
        offensive: float = 1.0,
        defensive: float = 1.0,
        team_id: str = "LEAGUE_AVG",
    ) -> "TeamStrength":
        # Baseline: neutralna drużyna = średnia ligowa (1.0, 1.0)
        return TeamStrength(
            team_id=team_id,
            likelihood=StrengthItem(offensive=offensive, defensive=defensive),
            posterior=StrengthItem(offensive=offensive, defensive=defensive),
            expected_goals=expected_goals,
            last_update=last_update,
            round_id=round_id,
        )


# @dataclass(frozen=True)
# class SeasonStats:
#     offensive: float
#     defensive: float


@dataclass(frozen=True)
class PagedResponse(Generic[T]):
    items: List[T]
    total_count: int
    sorting_option: str
    sorting_order: str

    @property
    def has_next(self) -> bool:
        return self.page_number < self.total_pages - 1


### ML entities
@dataclass(frozen=True)
class Synchronization:
    last_sync_date: str
    added_simulations: int


@dataclass(frozen=True)
class TrainingData:
    x_row: dict[str, Any]
    """Wektor cech (features) dla *jednego meczu* w postaci płaskiego słownika.
    Klucze to nazwy cech (np. 'home_p_off', 'away_l_def', 'diff_post_off'), a wartości to liczby/typy
    możliwe do wrzucenia do DataFrame i podania do XGBoost.
    
    To jest wejście modelu (X). Każdy TrainingData = 1 wiersz w DataFrame.
    """

    y_home: int
    """Target (etykieta) dla regresji bramek gospodarza.
    Oznacza liczbę goli zdobytych przez drużynę gospodarzy w tym meczu (wartość rzeczywista z symulacji/wykonania).
    
    To jest wyjście uczące dla modelu 'home goals'.
    """

    y_away: int
    """Target (etykieta) dla regresji bramek gości.
    Oznacza liczbę goli zdobytych przez drużynę gości w tym meczu (wartość rzeczywista z symulacji/wykonania).
    
    To jest wyjście uczące dla modelu 'away goals'.
    """

    prev_round_id: str
    """Identyfikator rundy (UUID) wskazujący snapshot wejściowych sił drużyn użyty do zbudowania x_row.
    W Twoim modelu TeamStrength jest stanem *po meczu*, więc żeby przewidzieć mecz rundy N,
    budujesz cechy z TeamStrength z rundy N-1 — i właśnie tę rundę reprezentuje prev_round_id.
    
    Użycia:
    - join: (team_id, prev_round_id) -> TeamStrength dla home/away,
    - split czasowy: pozwala przypisać rekord do kolejności rund (przez mapę LeagueRound: round_id -> round_no),
      bez mieszania przyszłości z przeszłością.
    """

@dataclass(frozen=True)
class TrainingDataset:
    train: List[TrainingData]
    test: List[TrainingData]

@dataclass(frozen=True)
class PredictRequest():
    league_id: str
    train_until_round_no: int
    train_ratio: float = 0.8
    ...