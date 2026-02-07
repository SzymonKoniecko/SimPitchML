from typing import Dict, List, Optional, Tuple
from src.domain.entities import (
    IterationResult,
    LeagueRound,
    MatchRound,
    TeamStrength,
    TrainingData,
)
from src.domain.features import Mapper
from src.core.logger import get_logger

logger = get_logger(__name__)
GUID_EMPTY = "00000000-0000-0000-0000-000000000000"


class TrainingBuilder:
    @staticmethod
    def build_dataset(
        iteration_result: IterationResult, league_rounds: List[LeagueRound]
    ) -> List[TrainingData]:
        if (
            iteration_result.simulated_match_rounds is None
            or len(iteration_result.simulated_match_rounds) == 0
        ):
            raise ValueError("Value cannot be None = simulated_match_rounds")
        if (
            iteration_result.team_strengths is None
            or len(iteration_result.team_strengths) == 0
        ):
            raise ValueError("Value cannot be None = team_strengths")
        if league_rounds is None or len(league_rounds) == 0:
            raise ValueError("Value cannot be None = league_rounds")
        
        return TrainingBuilder.build_dataset_from_scrap(
            match_results=iteration_result.simulated_match_rounds,
            team_strengths=iteration_result.team_strengths,
            league_rounds=league_rounds,
        )

    @staticmethod
    def build_dataset_from_scrap(
        match_results: List[MatchRound],
        team_strengths: List[TeamStrength],
        league_rounds: List[LeagueRound],
    ) -> List[TrainingData]:
        
        dataset: List[TrainingData] = []
        # Map: round_id -> prev_round_id (z uwzględnieniem Guid.Empty w Mapperze, jeśli to tam robisz)
        prev_round_id_by_round_id: Dict[str, str] = (
            Mapper.map_prev_round_id_by_round_id(
                Mapper.map_round_no_by_round_id(league_rounds)
            )
        )

        strength_map = TeamStrength.strength_map(team_strengths)

        for result in (r for r in match_results if r.is_played is True):
            prev_round_id = prev_round_id_by_round_id.get(result.round_id)
            if not prev_round_id:
                logger.error(
                    f"Missing prev_round_id for matchId={result.id}, round_id={result.round_id}"
                )
                continue  # albo: raise, jeśli to ma przerwać cały trening

            home_strength = strength_map.get((result.home_team_id, prev_round_id))
            away_strength = strength_map.get((result.away_team_id, prev_round_id))

            td = TrainingBuilder.build_single_training_data(
                match_result=result,
                home_strength=home_strength,
                away_strength=away_strength,
                prev_round_id=prev_round_id,
            )
            if td is not None:
                dataset.append(td)

        return dataset

    @staticmethod
    def build_single_training_data(
        match_result: MatchRound,
        home_strength: Optional[TeamStrength],
        away_strength: Optional[TeamStrength],
        prev_round_id: str,
    ) -> Optional[TrainingData]:

        if home_strength is None:
            logger.error(
                f"Missing home_strength teamId={match_result.home_team_id}, matchId={match_result.id}, prev_round_id={prev_round_id}"
            )
            return None

        if away_strength is None:
            logger.error(
                f"Missing away_strength teamId={match_result.away_team_id}, matchId={match_result.id}, prev_round_id={prev_round_id}"
            )
            return None

        X_row = {
            "home_p_off": home_strength.posterior.offensive,
            "home_p_def": home_strength.posterior.defensive,
            "home_l_off": home_strength.likelihood.offensive,
            "home_l_def": home_strength.likelihood.defensive,
            "away_p_off": away_strength.posterior.offensive,
            "away_p_def": away_strength.posterior.defensive,
            "away_l_off": away_strength.likelihood.offensive,
            "away_l_def": away_strength.likelihood.defensive,
            "diff_post_off": home_strength.posterior.offensive
            - away_strength.posterior.offensive,
            "diff_post_def": home_strength.posterior.defensive
            - away_strength.posterior.defensive,
        }

        return TrainingData(
            x_row=X_row,
            y_home=match_result.home_goals,
            y_away=match_result.away_goals,
            prev_round_id=prev_round_id,
        )
