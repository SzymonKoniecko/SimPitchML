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
        iteration_result: IterationResult,
        league_rounds: List[LeagueRound],
        match_rounds: List[
            MatchRound
        ],  # simulated_match_rounds but with the played matched BEFORE simulation
    ) -> List[TrainingData]:
        if match_rounds is None or len(match_rounds) == 0:
            raise ValueError("Value cannot be None = match_rounds")
        if (
            iteration_result.team_strengths is None
            or len(iteration_result.team_strengths) == 0
        ):
            raise ValueError("Value cannot be None = team_strengths")
        if league_rounds is None or len(league_rounds) == 0:
            raise ValueError("Value cannot be None = league_rounds")

        return TrainingBuilder.build_dataset_from_scrap(
            match_results=match_rounds,
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
        round_no_by_round_id = Mapper.map_round_no_by_round_id(league_rounds)

        strength_map = TeamStrength.strength_map(team_strengths)

        for result in (r for r in match_results if r.is_played is True):
            prev_round_id = prev_round_id_by_round_id.get(result.round_id)
            if not prev_round_id:
                logger.error(
                    f"Missing prev_round_id for matchId={result.id}, round_id={result.round_id}"
                )
                continue  # albo: raise, jeśli to ma przerwać cały trening

            league_avg_strength = (
                TeamStrength.league_average_baseline()
            )  # dodaj/zaimplementuj w encji, np. 1.0/1.0

            home_strength = TrainingBuilder.get_strength_or_fallback(
                strength_map,
                round_no_by_round_id,
                result.home_team_id,
                prev_round_id,
                league_avg_strength=league_avg_strength,
            )
            away_strength = TrainingBuilder.get_strength_or_fallback(
                strength_map,
                round_no_by_round_id,
                result.away_team_id,
                prev_round_id,
                league_avg_strength=league_avg_strength,
            )

            td = TrainingBuilder.build_single_training_data(
                match_round=result,
                home_strength=home_strength,
                away_strength=away_strength,
                prev_round_id=prev_round_id,
            )
            if td is not None:
                dataset.append(td)

        return dataset

    @staticmethod
    def get_strength_or_fallback(
        strength_map: Dict[Tuple[str, str], TeamStrength],
        round_no_by_round_id: Dict[str, int],
        team_id: str,
        prev_round_id: str,
        *,
        league_avg_strength: Optional[TeamStrength] = None,
    ) -> Optional[TeamStrength]:
        # 1) Exact match
        exact = strength_map.get((team_id, prev_round_id))
        if exact is not None:
            return exact

        # 2) LOCF: last snapshot with round_no < prev_round_no
        prev_no = round_no_by_round_id.get(prev_round_id)
        if prev_no is not None:
            best: Optional[TeamStrength] = None
            best_no: int = -1

            for (t_id, r_id), ts in strength_map.items():
                if t_id != team_id:
                    continue
                r_no = round_no_by_round_id.get(r_id)
                if r_no is None:
                    continue
                if r_no < prev_no and r_no > best_no:
                    best_no = r_no
                    best = ts

            if best is not None:
                return best

        logger.warning(f'\nLeague-average baseline used ! (TeamStrength) prev_roundId{prev_round_id} - teamId{team_id}\n')
        # 3) League-average baseline (attack=1, defense=1 etc.)
        league_avg_strength.team_id = team_id
        league_avg_strength.round_id = prev_round_id
        return league_avg_strength

    @staticmethod
    def build_single_training_data(
        match_round: MatchRound,
        home_strength: Optional[TeamStrength],
        away_strength: Optional[TeamStrength],
        prev_round_id: str,
    ) -> Optional[TrainingData]:

        if home_strength is None:
            logger.error(
                f"Missing home_strength teamId={match_round.home_team_id}, matchId={match_round.id}, prev_round_id={prev_round_id}"
            )
            return None

        if away_strength is None:
            logger.error(
                f"Missing away_strength teamId={match_round.away_team_id}, matchId={match_round.id}, prev_round_id={prev_round_id}"
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
            y_home=match_round.home_goals,
            y_away=match_round.away_goals,
            prev_round_id=prev_round_id,
        )
