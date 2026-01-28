from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, List

T = TypeVar("T")


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
    team_strengths: str
    simulated_match_rounds: str


@dataclass(frozen=True)
class PagedResponse(Generic[T]):
    items: List[T]
    total_count: int
    sorting_option: str
    sorting_order: str

    @property
    def has_next(self) -> bool:
        return self.page_number < self.total_pages - 1
