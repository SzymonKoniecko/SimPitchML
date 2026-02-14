from datetime import datetime
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
    def feature_schema() -> List[str]:
        """
        **Zwraca standardowy schemat cech (nazwy kolumn i kolejność) dla wszystkich X w projekcie.**

        To jest **stały kontrakt** między treningiem a predykcją: X_train i X_predict muszą mieć identyczne kolumny i kolejność.

        Zwraca zawsze tę samą listę (nie zależy od danych):
        ['home_p_off', 'home_p_def', 'home_l_off', 'home_l_def',
         'away_p_off', 'away_p_def', 'away_l_off', 'away_l_def',
         'diff_post_off', 'diff_post_def']

        Użycia:
        - W treningu: TrainingData.to_xy(..., feature_schema=TrainingData.feature_schema())
        - W predykcji: X_predict = Mapper.map_to_x_matrix(x_rows, TrainingData.feature_schema())
        - Zapis do metadanych: context.save(..., feature_schema=TrainingData.feature_schema())
        """
        return [
            # Gospodarz
            "home_p_off",  # home posterior offensive (długoterminowy atak)
            "home_p_def",  # home posterior defensive
            "home_l_off",  # home likelihood offensive (forma ataku)
            "home_l_def",  # home likelihood defensive
            # Gość
            "away_p_off",  # away posterior offensive
            "away_p_def",  # away posterior defensive
            "away_l_off",  # away likelihood offensive
            "away_l_def",  # away likelihood defensive
            # Różnice (derived)
            "diff_post_off",  # home_p_off - away_p_def (przewaga ataku gospodarza)
            "diff_post_def",  # home_p_def - away_p_off (przewaga obrony gospodarza)
        ]

    @staticmethod
    def build_dataset(
        iteration_result: IterationResult,
        match_rounds: List[
            MatchRound
        ],  # simulated_match_rounds but with the played matched BEFORE simulation
        prev_round_id_by_round_id: Dict[str, str],
        round_no_by_round_id: Dict[str, int],
        round_id_by_round_no: Dict[int, str],
        league_id: str,
        league_avg: str,
    ) -> List[TrainingData]:
        if match_rounds is None or len(match_rounds) == 0:
            raise ValueError("Value cannot be None = match_rounds")
        if (
            iteration_result.team_strengths is None
            or len(iteration_result.team_strengths) == 0
        ):
            raise ValueError("Value cannot be None = team_strengths")

        return TrainingBuilder.build_dataset_from_scrap(
            match_round=match_rounds,
            team_strengths=iteration_result.team_strengths,
            prev_round_id_by_round_id=prev_round_id_by_round_id,
            round_no_by_round_id=round_no_by_round_id,
            round_id_by_round_no=round_id_by_round_no,
            league_id=league_id,
            league_avg=league_avg,
        )

    @staticmethod
    def build_dataset_from_scrap(
        match_round: List[MatchRound],
        team_strengths: List[TeamStrength],
        prev_round_id_by_round_id: Dict[str, str],
        round_no_by_round_id: Dict[str, int],
        round_id_by_round_no: Dict[int, str],
        league_id: str,
        league_avg: str,
    ) -> List[TrainingData]:

        dataset: List[TrainingData] = []

        strength_map = TeamStrength.strength_map_from_list(team_strengths)

        for m_result in (r for r in match_round if r.is_played is True):
            prev_round_id = prev_round_id_by_round_id.get(m_result.round_id)
            if prev_round_id == None:
                prev_round_id = m_result.round_id

            home_strength = TrainingBuilder.get_strength_or_fallback(
                strength_map,
                round_no_by_round_id,
                round_id_by_round_no,
                m_result,
                True,
                prev_round_id,
                league_id=league_id,
                league_avg_strength=league_avg,
            )
            away_strength = TrainingBuilder.get_strength_or_fallback(
                strength_map,
                round_no_by_round_id,
                round_id_by_round_no,
                m_result,
                False,
                prev_round_id,
                league_id=league_id,
                league_avg_strength=league_avg,
            )

            td = TrainingBuilder.build_single_training_data(
                match_round=m_result,
                home_strength=home_strength,
                away_strength=away_strength,
                prev_round_id=prev_round_id,
            )
            if td is not None:
                dataset.append(td)

        return dataset

    @staticmethod
    def get_strength_or_fallback(
        strength_map: Dict[Tuple[str, str], List[TeamStrength]],
        round_no_by_round_id: Dict[str, int],
        round_id_by_round_no: Dict[int, str],
        match_round: MatchRound,
        is_home: bool,
        prev_round_id: str,
        *,
        league_id: str,
        league_avg_strength: Optional[float] = None,
    ) -> TeamStrength:
        team_id = match_round.home_team_id if is_home else match_round.away_team_id

        def newest(strengths: List[TeamStrength]) -> Optional[TeamStrength]:
            if strengths is None:
                return None
            if isinstance(strengths, TeamStrength):
                return strengths
            if not strengths:
                return None
            return max(strengths, key=lambda x: x.last_update)

        def updateStatsByMatchRound(
            ts: TeamStrength, is_incoming_match: bool
        ) -> TeamStrength:
            if is_incoming_match:  # incoming match does't have home/away goals.
                return ts.with_posterior(25, league_avg_strength)
            return (
                ts.with_incremented_stats(match_round, is_home_team=is_home)
                .with_likelihood()
                .with_posterior(25, league_avg_strength)
            )

        # 1) Exact match
        strengths = strength_map.get((team_id, prev_round_id))
        ts = newest(strengths) if strengths else None
        if ts is not None:
            return ts

        # 2) Walk back rounds: prev_round_no-1, prev_round_no-2, ...
        prev_no = round_no_by_round_id.get(prev_round_id)
        if prev_no is not None:
            for no in range(prev_no - 1, -1, -1):
                rid = round_id_by_round_no.get(no)
                if not rid:
                    continue

                strengths = strength_map.get((team_id, rid))
                ts = newest(strengths) if strengths else None
                if ts is not None:
                    logger.warning(
                        "(prev TeamStrength found), New strength will be created. team_id=%s prev_round_id=%s avg=%s",
                        team_id,
                        prev_round_id,
                        league_avg_strength,
                    )
                    base_home = ts.with_round_meta(
                        prev_round_id, datetime.now().isoformat()
                    )
                    return updateStatsByMatchRound(
                        base_home,
                        match_round.home_goals is None
                        or match_round.away_goals is None,
                    )

        if league_avg_strength is None:
            raise ValueError(
                "league_avg_strength is required when falling back to baseline"
            )

        logger.warning(
            "League-average baseline used (no TeamStrength found). team_id=%s prev_round_id=%s avg=%s",
            team_id,
            prev_round_id,
            league_avg_strength,
        )

        return updateStatsByMatchRound(
            TeamStrength.get_team_strength_average_baseline(
                round_id=prev_round_id,
                last_update=datetime.now().isoformat(),
                expected_goals=0.00,
                offensive=float(league_avg_strength),
                defensive=float(league_avg_strength),
                team_id=team_id,
                league_id=league_id,
                league_strength=league_avg_strength,
            ),
            match_round.home_goals is None or match_round.away_goals is None,
        )

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

        schema = TrainingBuilder.feature_schema()

        X_row = dict.fromkeys(schema, 0.0)  # Pre-fill zerami wszystkie cechy z schema

        X_row["home_p_off"] = home_strength.posterior.offensive
        X_row["home_p_def"] = home_strength.posterior.defensive
        X_row["home_l_off"] = home_strength.likelihood.offensive
        X_row["home_l_def"] = home_strength.likelihood.defensive
        X_row["away_p_off"] = away_strength.posterior.offensive
        X_row["away_p_def"] = away_strength.posterior.defensive
        X_row["away_l_off"] = away_strength.likelihood.offensive
        X_row["away_l_def"] = away_strength.likelihood.defensive
        X_row["diff_post_off"] = (
            home_strength.posterior.offensive - away_strength.posterior.offensive
        )
        X_row["diff_post_def"] = (
            home_strength.posterior.defensive - away_strength.posterior.defensive
        )

        return TrainingData(
            x_row=X_row,
            y_home=match_round.home_goals,
            y_away=match_round.away_goals,
            prev_round_id=prev_round_id,
        )
