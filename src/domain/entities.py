from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, List
import json

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
    simulated_match_rounds: List[MatchResult]

    @staticmethod
    def from_team_strength_raw(data: Union[str, List[Dict]]) -> List[TeamStrength]:
        if data is None:
            return []
            
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode TeamStrength JSON: {data[:100]}...") # Log snippet only
                return [] 

        return [
            TeamStrength(
                team_id=item.get("TeamId") or item.get("team_id"), 
                likelihood=StrengthItem(
                    offensive=item["Likelihood"]["Offensive"],
                    defensive=item["Likelihood"]["Defensive"]
                ),
                posterior=StrengthItem(
                    offensive=item["Posterior"]["Offensive"],
                    defensive=item["Posterior"]["Defensive"]
                ),
                expected_goals=str(item.get("ExpectedGoals", 0.0)), # Safe access + string conversion
                last_update=item["LastUpdate"],
                round_id=item.get("RoundId") or item.get("round_id") 
            ) 
            for item in data
        ]
    
    @staticmethod
    def from_sim_matches_raw(data: Union[str, List[Dict]]) -> List[MatchResult]:
        if data is None:
            return []

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return []
        
        return [
            MatchResult(
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
class MatchResult:
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


@dataclass(frozen=True)
class TeamStrength:
    team_id: str
    likelihood: StrengthItem
    posterior: StrengthItem
    expected_goals: str
    last_update: str
    round_id: str
    #season_stats: int

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


@dataclass(frozen=True)
class Synchronization:
    last_sync_date: str
    added_simulations: int