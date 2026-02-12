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
            "home_p_off",    # home posterior offensive (długoterminowy atak)
            "home_p_def",    # home posterior defensive
            "home_l_off",    # home likelihood offensive (forma ataku)
            "home_l_def",    # home likelihood defensive
            
            # Gość
            "away_p_off",    # away posterior offensive
            "away_p_def",    # away posterior defensive
            "away_l_off",    # away likelihood offensive
            "away_l_def",    # away likelihood defensive
            
            # Różnice (derived)
            "diff_post_off", # home_p_off - away_p_def (przewaga ataku gospodarza)
            "diff_post_def", # home_p_def - away_p_off (przewaga obrony gospodarza)
        ]
    
    @staticmethod
    def build_dataset(
        iteration_result: IterationResult,
        league_rounds: List[LeagueRound],
        match_rounds: List[
            MatchRound
        ],  # simulated_match_rounds but with the played matched BEFORE simulation
        prev_round_id_by_round_id: Dict[str, str]
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
            prev_round_id_by_round_id=prev_round_id_by_round_id
        )

    @staticmethod
    def build_dataset_from_scrap(
        match_results: List[MatchRound],
        team_strengths: List[TeamStrength],
        league_rounds: List[LeagueRound],
        prev_round_id_by_round_id: Dict[str, str]
    ) -> List[TrainingData]:

        dataset: List[TrainingData] = []

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
        league_avg_strength: Optional[float] = None,
    ) -> TeamStrength:
        
        # 1) Exact match
        exact = strength_map.get((team_id, prev_round_id))
        if exact is not None:
            return exact

        prev_no = round_no_by_round_id.get(prev_round_id)

        # 2) LOCF: last snapshot with round_no < prev_no
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

        # 3) Any snapshot for that team (fallback if no earlier one exists)
        any_ts: Optional[TeamStrength] = None
        any_best_no: int = -1

        for (t_id, r_id), ts in strength_map.items():
            if t_id != team_id:
                continue

            # jeśli mamy round_no, wybierz „najświeższy”
            r_no = round_no_by_round_id.get(r_id)
            if r_no is None:
                # jak nie umiemy porównać, zachowaj pierwszy lepszy
                if any_ts is None:
                    any_ts = ts
                continue

            if r_no > any_best_no:
                any_best_no = r_no
                any_ts = ts

        if any_ts is not None:
            return any_ts

        # 4) League-average baseline (gdy nie ma żadnego TeamStrength)
        avg = league_avg_strength if league_avg_strength is not None else 1.0

        logger.warning(
            "League-average baseline used (no TeamStrength found). team_id=%s prev_round_id=%s avg=%s",
            team_id, prev_round_id, avg
        )

        return TeamStrength.league_average_baseline(
            team_id=team_id,
            round_id=prev_round_id,
            offensive=float(avg),
            defensive=float(avg),
            last_update=datetime.utcnow().isoformat(),
            expected_goals="N/A",
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
