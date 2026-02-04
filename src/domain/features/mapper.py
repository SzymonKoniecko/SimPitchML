from typing import Dict, List, Tuple

from src.domain.entities import LeagueRound


class Mapper:
    def __init__(self):
        pass

    @staticmethod
    def Map_round_id_by_round_number(rounds: List[LeagueRound]) -> Dict[Tuple[str, str], LeagueRound]:
        rounds_sorted = sorted(rounds, key=lambda x: x.round, reverse=False)

        return {(r.round, r.Id) for r in rounds_sorted}

    @staticmethod
    def Map_list_of_round_for_round_id(rounds: Dict[Tuple[str, str], LeagueRound]) -> Dict[int, str]:
        """
        returns => key: number of round - value: round_id
        """

        map_of_rounds = {}

        for value in rounds.keys:
            if rounds[value]:
                pass

    @staticmethod
    def Map_prev_round_id_by_round_id(rounds: Dict[str, LeagueRound]):
        """
        Its a key for '-1' rounds, because we are using current TeamStreangth before given match
        """
        prev_round_id_by_round_id = {}

        for (index, value) in rounds:
            curr = value
            if index == 0:

                pass