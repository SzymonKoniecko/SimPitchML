from typing import Dict, List, Tuple

from src.domain.entities import LeagueRound


class Mapper:
    def __init__(self):
        pass

    @staticmethod
    def map_round_id_by_round_number(rounds: List[LeagueRound]) -> Dict[int, str]:
        rounds_sorted = sorted(rounds, key=lambda x: x.round, reverse=False)
        return {r.round: r.id for r in rounds_sorted}

    @staticmethod
    def Map_prev_round_id_by_round(rounds: Dict[int, str]):
        """
        Input:  {2: "r2", 3: "r3"}
        Output: {2: "r1", 3: "r2"}  (prev round id for each round number)
        """
        prev_round_id_by_round = {}

        for round_no, round_id in rounds.items():
            prev_id = rounds.get(round_no - 1)
            if prev_id is not None:
                prev_round_id_by_round[round_no] = prev_id

        return prev_round_id_by_round