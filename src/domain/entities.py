from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict, field, replace
from itertools import chain
from typing import (
    Any,
    DefaultDict,
    Dict,
    Generic,
    Iterable,
    Optional,
    Tuple,
    TypeVar,
    List,
    Union,
)
import json
import uuid


import pandas as pd
from xgboost import XGBRegressor

T = TypeVar("T")

from src.core import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SimulationOverview:
    id: str
    created_date: str
    league_strengths: str
    prior_league_strength: float


@dataclass(frozen=False)
class IterationResult:
    id: str
    simulation_id: str
    iteration_index: int
    start_date: str
    execution_time: str
    team_strengths: List[TeamStrength]
    simulated_match_rounds: List[MatchRound]

    @staticmethod
    def team_strengths_to_json_value(team_strengths: List[TeamStrength]) -> str:
        """Convert List[TeamStrength] to JSON string."""
        # asdict rekurencyjnie konwertuje nested dataclasses na dict
        dict_list = [asdict(ts) for ts in team_strengths]
        return json.dumps(dict_list, indent=2)

    @staticmethod
    def simulated_match_rounds_to_json_value(match_rounds: List[MatchRound]) -> str:
        """Convert List[MatchRound] to JSON string."""
        dict_list = [asdict(mr) for mr in match_rounds]
        return json.dumps(dict_list, indent=2)

    @staticmethod
    def from_team_strength_raw_list(
        data: Union[str, List[Dict[str, Any]], Dict[str, Any]],
    ) -> List[TeamStrength]:
        if not data:
            return []

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode TeamStrength JSON: {data[:100]}...")
                return []

        # Dict[str, List[...]] -> flatten
        if isinstance(data, dict):
            flattened: List[Dict[str, Any]] = []
            for _key, value in data.items():
                if isinstance(value, list):
                    flattened.extend([v for v in value if isinstance(v, dict)])
                elif isinstance(value, dict):
                    flattened.append(value)
            data = flattened

        if not isinstance(data, list):
            logger.error(f"Unexpected TeamStrength payload type: {type(data)}")
            return []

        result: List[TeamStrength] = []
        for item in data:
            if not isinstance(item, dict):
                continue

            likelihood = item.get("Likelihood") or item.get("likelihood") or {}
            posterior = item.get("Posterior") or item.get("posterior") or {}

            ts = TeamStrength(
                team_id=item.get("TeamId")
                or item.get("team_id")
                or str(uuid.UUID(int=0)),
                likelihood=StrengthItem(
                    offensive=float(
                        likelihood.get("Offensive")
                        or likelihood.get("offensive")
                        or likelihood.get("Item1")
                        or 1.0
                    ),
                    defensive=float(
                        likelihood.get("Defensive")
                        or likelihood.get("defensive")
                        or likelihood.get("Item2")
                        or 1.0
                    ),
                ),
                posterior=StrengthItem(
                    offensive=float(
                        posterior.get("Offensive")
                        or posterior.get("offensive")
                        or posterior.get("Item1")
                        or 1.0
                    ),
                    defensive=float(
                        posterior.get("Defensive")
                        or posterior.get("defensive")
                        or posterior.get("Item2")
                        or 1.0
                    ),
                ),
                expected_goals=float(
                    item.get("ExpectedGoals") or item.get("expected_goals") or 0.0
                ),
                last_update=item.get("LastUpdate")
                or item.get("last_update")
                or "2001-01-01T05:14:36.246303",
                round_id=item.get("RoundId")
                or item.get("round_id")
                or str(uuid.UUID(int=0)),
                season_stats=SeasonStats.map_from_grpc(item.get("SeasonStats")),
            )

            # opcjonalnie: pomiń jeśli brak team_id
            if not ts.team_id:
                continue

            result.append(ts)

        return result

    @staticmethod
    def from_team_strength_raw_dict(
        data: Union[str, List[Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, List[TeamStrength]]:
        # 1) użyj Twojej logiki parsowania -> List[TeamStrength]
        item_list: List[TeamStrength] = IterationResult.from_team_strength_raw_list(
            data
        )

        grouped: DefaultDict[str, List[TeamStrength]] = defaultdict(list)
        for ts in item_list:
            if not ts.team_id:
                continue
            grouped[ts.team_id].append(ts)

        return dict(grouped)

    @staticmethod
    def from_sim_matches_raw_new(
        data: Union[str, List[Dict[str, Any]]],
    ) -> List[MatchRound]:
        if data is None:
            return []

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return []

        if not isinstance(data, list):
            return []

        return [
            MatchRound(
                id=item.get("Id") or item.get("id") or str(uuid.UUID(int=0)),
                round_id=item.get("RoundId")
                or item.get("round_id")
                or str(uuid.UUID(int=0)),
                home_team_id=item.get("HomeTeamId") or item.get("home_team_id"),
                away_team_id=item.get("AwayTeamId") or item.get("away_team_id"),
                home_goals=item.get("HomeGoals", 0),
                away_goals=item.get("AwayGoals", 0),
                is_draw=item.get("IsDraw", False),
                is_played=item.get("IsPlayed", True),
            )
            for item in data
            if isinstance(item, dict)
        ]

    @staticmethod
    def to_pretty_string(self) -> str:
        import dataclasses
        import json

        data_dict = dataclasses.asdict(self)

        return json.dumps(data_dict, indent=4, default=str)


@dataclass(frozen=False)
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


@dataclass(frozen=False)
class StrengthItem:
    offensive: float
    defensive: float


@dataclass(frozen=False)
class TeamStrength:
    team_id: str
    likelihood: StrengthItem
    posterior: StrengthItem
    expected_goals: float
    last_update: str
    round_id: str
    season_stats: SeasonStats = field(
        default_factory=lambda: SeasonStats.empty(team_id=str(uuid.UUID(int=0)))
    )
    # ^ default_factory

    @staticmethod
    def strength_map_from_list(
        items: List[TeamStrength],
    ) -> Dict[Tuple[str, str], List[TeamStrength]]:
        grouped: DefaultDict[Tuple[str, str], List[TeamStrength]] = defaultdict(list)

        for ts in items:
            if not ts.team_id or not ts.round_id:
                raise ValueError("Missing team_id or round_id in strength_map")
            grouped[(ts.team_id, ts.round_id)].append(ts)

        for lst in grouped.values():
            lst.sort(key=lambda x: x.last_update, reverse=True)

        return dict(grouped)

    @staticmethod
    def strength_map_to_list(
        strength_map: Dict[Tuple[str, str], List["TeamStrength"]],
    ) -> List["TeamStrength"]:
        def as_list(
            v: Union[List["TeamStrength"], "TeamStrength"],
        ) -> List["TeamStrength"]:
            return v if isinstance(v, list) else [v]

        return list(chain.from_iterable(as_list(v) for v in strength_map.values()))

    @staticmethod
    def strength_map_from_dict(
        items: Dict[str, List[TeamStrength]],
    ) -> Dict[Tuple[str, str], List[TeamStrength]]:
        grouped: DefaultDict[Tuple[str, str], List[TeamStrength]] = defaultdict(list)

        for team_strengths in items.values():
            for ts in team_strengths:
                if not ts.team_id or not ts.round_id:
                    raise ValueError("Missing team_id or round_id in strength_map")
                grouped[(ts.team_id, ts.round_id)].append(ts)

        for lst in grouped.values():
            lst.sort(key=lambda x: x.last_update, reverse=True)

        return dict(grouped)

    @staticmethod
    def add_to_strength_map(
        strength_map: Dict[Tuple[str, str], "TeamStrength"],
        ts: "TeamStrength",
    ) -> Dict[Tuple[str, str], "TeamStrength"]:
        if not isinstance(ts, TeamStrength):
            raise TypeError(f"Expected TeamStrength, got {type(ts).__name__}")

        key = (ts.team_id, ts.round_id)
        new_map = dict(strength_map)
        new_map[key] = ts
        return new_map

    @classmethod
    def merge_strength_maps(
        cls, *maps: Dict[Tuple[str, str], "TeamStrength"]
    ) -> Dict[Tuple[str, str], "TeamStrength"]:
        combined: Dict[Tuple[str, str], TeamStrength] = {}
        for m in maps:
            combined.update(m)
        return combined

    # @staticmethod
    # def strength_map_to_list(strength_map: Dict[Tuple[str, str], "TeamStrength"]) -> List###["TeamStrength"]:
    #     return list(strength_map.values())

    @staticmethod
    def get_team_strength_average_baseline(
        round_id: str = str(uuid.UUID(int=0)),
        last_update: str = "2001-01-01T22:00:00.000000",
        expected_goals: float = 1.0,
        offensive: float = 1.0,
        defensive: float = 1.0,
        team_id: str = str(uuid.UUID(int=0)),
        season_year: int = 3,  # enum seasonYear has 3 as 2025/2026
        league_id: str = str(uuid.UUID(int=0)),
        league_strength: float = 1.0,
    ) -> "TeamStrength":
        return TeamStrength(
            team_id=team_id,
            likelihood=StrengthItem(
                offensive=float(offensive), defensive=float(defensive)
            ),
            posterior=StrengthItem(
                offensive=float(offensive), defensive=float(defensive)
            ),
            expected_goals=expected_goals,
            last_update=last_update,
            round_id=round_id,
            season_stats=SeasonStats.empty(
                team_id=team_id,
                season_year=season_year,
                league_id=league_id,
                league_strength=league_strength,
                id=str(uuid.uuid4()),
            ),
        )

    def with_round_meta(self, round_id: str, last_update: str) -> "TeamStrength":
        return replace(self, round_id=round_id, last_update=last_update)

    def with_incremented_stats(
        self, match_round: MatchRound, is_home_team: bool
    ) -> "TeamStrength":
        return replace(
            self, season_stats=self.season_stats.incremented(match_round, is_home_team)
        )

    def with_likelihood(self) -> "TeamStrength":
        if self.season_stats.matches_played == 0:
            raise ValueError("Cannot calculate likelihood without matches played.")
        like = StrengthItem(
            offensive=self.season_stats.goals_for / self.season_stats.matches_played,
            defensive=self.season_stats.goals_against
            / self.season_stats.matches_played,
        )
        return replace(self, likelihood=like)

    def with_posterior(
        self, games_to_reach_trust: int, league_strength: float
    ) -> "TeamStrength":
        if games_to_reach_trust <= 0:
            raise ValueError("games_to_reach_trust must be greater than zero.")

        beta_0 = float(games_to_reach_trust)
        updated_league_strength = (
            float(league_strength) + float(self.season_stats.league_strength)
        ) / 2.0
        alpha_0 = beta_0 * updated_league_strength

        ss = replace(self.season_stats, league_strength=updated_league_strength)

        posterior_beta = beta_0 + float(ss.matches_played)
        posterior = StrengthItem(
            offensive=(alpha_0 + float(ss.goals_for)) / posterior_beta,
            defensive=(alpha_0 + float(ss.goals_against)) / posterior_beta,
        )

        return replace(
            self,
            season_stats=ss,
            posterior=posterior,
            expected_goals=float(posterior.offensive),
        )


@dataclass(frozen=False)
class SeasonStats:
    id: str
    team_id: str
    season_year: str
    league_id: str
    league_strength: float
    matches_played: int
    wins: int
    losses: int
    draws: int
    goals_for: int
    goals_against: int

    @staticmethod
    def empty(
        *,
        team_id: str,
        season_year: int = 3,
        league_id: str = str(uuid.UUID(int=0)),
        league_strength: float = 1.0,
        id: str = str(uuid.UUID(int=0)),
    ) -> "SeasonStats":
        return SeasonStats(
            id=id,
            team_id=team_id,
            season_year=season_year,
            league_id=league_id,
            league_strength=league_strength,
            matches_played=0,
            wins=0,
            losses=0,
            draws=0,
            goals_for=0,
            goals_against=0,
        )

    @staticmethod
    def map_from_grpc(item: Any) -> "SeasonStats":
        return SeasonStats(
            id=item.get("Id"),
            team_id=item.get("TeamId"),
            season_year=item.get("SeasonYear"),
            league_id=item.get("LeagueId"),
            league_strength=item.get("LeagueStrength"),
            matches_played=item.get("MatchesPlayed"),
            wins=item.get("Wins"),
            losses=item.get("Losses"),
            draws=item.get("Draws"),
            goals_for=item.get("GoalsFor"),
            goals_against=item.get("GoalsAgainst"),
        )

    def incremented(self, match_round: MatchRound, is_home_team: bool) -> "SeasonStats":
        if match_round.home_goals is None or match_round.away_goals is None:
            raise ValueError(
                f"Home goals or away goals are null. MatchRoundId:{match_round.id}"
            )

        matches_played = self.matches_played + 1
        wins, losses, draws = self.wins, self.losses, self.draws
        goals_for, goals_against = self.goals_for, self.goals_against
        team_id = ""
        if is_home_team:
            team_id = match_round.home_team_id
            gf, ga = match_round.home_goals, match_round.away_goals
            if gf > ga:
                wins += 1
            elif gf < ga:
                losses += 1
            else:
                draws += 1
        else:
            team_id = match_round.away_team_id
            gf, ga = match_round.away_goals, match_round.home_goals
            if gf > ga:
                wins += 1
            elif gf < ga:
                losses += 1
            else:
                draws += 1

        goals_for += gf
        goals_against += ga

        return replace(
            self,
            id=str(uuid.uuid4()),
            team_id=team_id,
            matches_played=matches_played,
            wins=wins,
            losses=losses,
            draws=draws,
            goals_for=goals_for,
            goals_against=goals_against,
        )

    @staticmethod
    def merge(accumulator: "SeasonStats", new_data: "SeasonStats") -> "SeasonStats":
        if accumulator.team_id != new_data.team_id:
            raise ValueError(
                f"Cannot merge SeasonStats for different teams: {accumulator.team_id} != {new_data.team_id}"
            )

        new_league_strength = (
            accumulator.league_strength + new_data.league_strength
        ) / 2.0

        return SeasonStats(
            id=new_data.id,
            team_id=new_data.team_id,
            season_year=new_data.season_year,
            league_id=new_data.league_id,
            league_strength=new_league_strength,
            matches_played=accumulator.matches_played + new_data.matches_played,
            wins=accumulator.wins + new_data.wins,
            losses=accumulator.losses + new_data.losses,
            draws=accumulator.draws + new_data.draws,
            goals_for=accumulator.goals_for + new_data.goals_for,
            goals_against=accumulator.goals_against + new_data.goals_against,
        )


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
class PredictRequest:
    simulation_id: str
    league_id: str
    iteration_count: int
    team_strengths: Dict[
        str, List[TeamStrength]
    ]  # remember -  List[TeamStrength] in IterationResult
    matches_to_simulate: List[MatchRound]
    train_until_round_no: int
    league_avg_strength: Optional[float] = None
    seed: Optional[int] = None
    train_ratio: Optional[float] = None
    games_to_reach_trust: Optional[int] = None


@dataclass(frozen=True)
class TrainedModels:
    home: XGBRegressor
    away: XGBRegressor
    feature_schema: list[str]


@dataclass(frozen=True)
class TrainingDataset:
    train: List[TrainingData]
    test: List[TrainingData]


@dataclass(frozen=True)
class InitPrediction:
    training_dataset: TrainingDataset
    list_simulation_ids: List[str]
    prev_round_id_by_round_id: Dict[str, str]
    round_no_by_round_id: Dict[str, int]
    round_id_by_round_no: Dict[int, str]
