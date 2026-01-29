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
                logger.error(f"Failed to decode JSON: {data}")
                return [] 

        
        # FIX: Manually instantiate nested StrengthItem objects
        # We assume the JSON keys match the dataclass fields (team_id vs TeamId needs handling)
        return [
            TeamStrength(
                team_id=item.get("TeamId") or item.get("team_id"), # Handle capitalization fallback
                likelihood=StrengthItem(
                    offensive=item["Likelihood"]["Offensive"],
                    defensive=item["Likelihood"]["Defensive"]
                ),
                posterior=StrengthItem(
                    offensive=item["Posterior"]["Offensive"],
                    defensive=item["Posterior"]["Defensive"]
                ),
                expected_goals=str(item["ExpectedGoals"]), # Ensure string type
                last_update=item["LastUpdate"],
                round_id=item["RoundId"]
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
        
        # Simple unpacking works here since MatchResult has no nested objects
        # Assumes JSON keys match fields exactly. If casing differs (Id vs id), map manually like above.
        return [MatchResult(**item) for item in data]

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
class StrengthItem:
    offensive: float
    defensive: float

# @dataclass(frozen=True)
# class SeasonStats:
#     offensive: float
#     defensive: float

@dataclass(frozen=True)
class TeamStrength:
    team_id: str
    likelihood: StrengthItem
    posterior: StrengthItem
    expected_goals: str
    last_update: str
    round_id: str
    #season_stats: int



@dataclass(frozen=True)
class PagedResponse(Generic[T]):
    items: List[T]
    total_count: int
    sorting_option: str
    sorting_order: str

    @property
    def has_next(self) -> bool:
        return self.page_number < self.total_pages - 1
