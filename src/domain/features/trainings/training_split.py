from typing import Dict, List, Optional, Tuple
from src.domain.entities import TrainingData


class TrainingSplit:
    @staticmethod
    def define_train_split(
        dataset: List[TrainingData],
        round_no_by_round_id: Dict[str, int],
        train_until_round_no: Optional[int] = None,
        train_ratio: float = 0.8,
    ) -> Tuple[List[TrainingData], List[TrainingData]]:
        """
        Splituje dataset po rundach (czasowo), bez shuffle.

        - Jeśli podasz train_until_round_no: train = rundy <= N, test = rundy > N.
        - Jeśli nie podasz: wyznacza cutoff po liczbie rund na bazie train_ratio.

        :param dataset: Pełny dataset do splitu.
        :param round_no_by_round_id: Mapa {round_id -> round_no}.
        :param train_until_round_no: Jawny cutoff rundy treningowej (N).
        :param train_ratio: Jeśli brak cutoff, ile rund ma iść do treningu (0..1).
        :return: (train, test)
        """
        if not dataset:
            return [], []

        # 1) Odfiltruj rekordy bez znanego round_no (bo nie ma rundy 0 w LeagueRound)
        sortable: List[tuple[int, TrainingData]] = []
        for item in dataset:
            round_no = round_no_by_round_id.get(item.prev_round_id)
            if round_no is None:
                continue
            sortable.append((round_no, item))

        if not sortable:
            return [], []

        # 2) Sortowanie czasowe po round_no (1..38)
        sortable.sort(key=lambda t: t[0])  # [web:61]

        # 3) Wyznacz cutoff
        unique_rounds = sorted({rn for rn, _ in sortable})
        if train_until_round_no is None:
            # cutoff po liczbie rund, a nie po liczbie rekordów (stabilniejsze w piłce)
            k = max(1, int(len(unique_rounds) * train_ratio))
            train_until_round_no = unique_rounds[k - 1]

        # 4) Split
        train: List[TrainingData] = []
        test: List[TrainingData] = []

        for rn, item in sortable:
            if rn <= train_until_round_no:
                train.append(item)
            else:
                test.append(item)

        return train, test
