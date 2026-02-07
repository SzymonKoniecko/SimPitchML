from typing import Dict, List, Optional, Tuple
from src.domain.entities import TrainingData, TrainingDataset
from src.core.logger import get_logger

logger = get_logger(__name__)

class TrainingSplit:
    @staticmethod
    def define_train_split(
        dataset: List[TrainingData],
        round_no_by_round_id: Dict[str, int],
        train_until_round_no: Optional[int] = None,
        train_ratio: float = 0.8,
    ) -> TrainingDataset:
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

        min_rn = unique_rounds[0]
        max_rn = unique_rounds[-1]

        if train_until_round_no is not None:
            if train_until_round_no < min_rn:
                logger.warning(
                    "Split: All data will go to TEST because cutoff_round=%s is below min_round_in_data=%s "
                    "(no rn <= cutoff). Consider increasing train_until_round_no or using ratio-based split.",
                    train_until_round_no, min_rn
                )
            elif train_until_round_no >= max_rn:
                logger.warning(
                    "Split: All data will go to TRAIN because cutoff_round=%s is >= max_round_in_data=%s "
                    "(all rn <= cutoff). Consider decreasing train_until_round_no.",
                    train_until_round_no, max_rn
                )
        else:
            if len(unique_rounds) == 1:
                logger.warning(
                    "Split: Only one unique round (%s) present in data; time-based split will be degenerate "
                    "(train or test may be empty depending on cutoff).",
                    unique_rounds[0]
                )

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

        from collections import Counter
        counts = Counter(rn for rn, _ in sortable)
        logger.info(
            "Split: rounds_hist=" +
            ", ".join(f"{rn}:{counts[rn]}" for rn in unique_rounds)
        )

        return TrainingDataset(train=train, test= test)
