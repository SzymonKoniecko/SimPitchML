from typing import Optional, Tuple
import xgboost as xgb

from src.core import get_logger
from src.di.ports.adapters.json_file_repository_port import JsonFileRepositoryPort

EXTENSION = "json"
logger = get_logger(__name__)


class XgBoostContextService:
    def __init__(self, repo: JsonFileRepositoryPort):
        self.repo = repo

    def save_league_model(self, model: xgb.Booster, home_or_away: str, league_id: str):
        filename = f"xgboost_{home_or_away}_{league_id}.{EXTENSION}"
        full_path_object = self.repo.get_full_path(filename)

        #  Path object =>  string, beacuse  XGBoost needs it
        full_path_str = str(full_path_object)

        model.save_model(full_path_str)
        logger.info(f">> Model XGBoost({home_or_away}) saved in: {full_path_str}")

    def save_league_models(
        self, model_home: xgb.Booster, model_away: xgb.Booster, league_id: str
    ):
        self.save_league_model(
            model=model_home, home_or_away="home", league_id=league_id
        )
        self.save_league_model(
            model=model_away, home_or_away="away", league_id=league_id
        )

    def load_league_model(
        self, home_or_away: str, league_id: str
    ) -> Optional[xgb.Booster]:
        filename = f"xgboost_{home_or_away}_{league_id}.{EXTENSION}"
        full_path_object = self.repo.get_full_path(filename)

        if not full_path_object.exists():
            return xgb.Booster()

        model = xgb.Booster()
        model.load_model(str(full_path_object))
        model
        logger.info(">> Model XGBOOST({home_or_away}) loaded - name:{filename}")
        return model

    def load_league_models(self, league_id: str) -> Tuple[xgb.Booster, xgb.Booster]:
        return self.load_league_model(
            home_or_away="home", league_id=league_id
        ), self.load_league_model(home_or_away="away", league_id=league_id)
