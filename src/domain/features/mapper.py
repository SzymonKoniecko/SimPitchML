from typing import Dict, List, Tuple

from src.domain.entities import LeagueRound

GUID_EMPTY = "00000000-0000-0000-0000-000000000000"

class Mapper:
    def __init__(self):
        pass

    @staticmethod
    def map_round_no_by_round_id(rounds: List[LeagueRound]) -> Dict[str, int]:
        rounds_sorted = sorted(rounds, key=lambda x: x.round, reverse=False)
        return {r.id: r.round for r in rounds_sorted}

    @staticmethod
    def map_prev_round_id_by_round_id(rounds: Dict[str, int]) -> Dict[str, str]:
        """
        Input:  {"r2":2,"r3":3}
        Output: {"r2":"r1","r3":"r2"} (prev round id for each round id)

        *Risk if roundId is null* Currently its Guid.Empty
        """

        id_by_no: Dict[int, str] = {round_no: round_id for round_id, round_no in rounds.items()}

        prev_by_id: Dict[str, str] = {}

        for round_id, round_no in rounds.items():
            prev_round_id = id_by_no.get(round_no - 1, GUID_EMPTY)
            prev_by_id[round_id] = prev_round_id

        return prev_by_id