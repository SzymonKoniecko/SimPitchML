from typing import Optional
import xgboost as xgb

from src.core import get_logger
from src.adapters.persistence.json_repository import JsonFileRepository

EXTENSION = "json"
logger = get_logger(__name__) 

class XgBoostContextService:
    def __init__(self, repo: JsonFileRepository):
        self.repo = repo

    def save_league_model(self, model: xgb.Booster, league_id: str):
        filename = f"xgboost_{league_id}.{EXTENSION}"
        full_path_object = self.repo.get_full_path(filename)
        
        #  Path object =>  string, beacuse  XGBoost needs it
        full_path_str = str(full_path_object)
        
        model.save_model(full_path_str)
        logger.info(f">> Model XGBoost saved in: {full_path_str}")

    def load_league_model(self, league_id: str) -> Optional[xgb.Booster]:
        filename = f"xgboost_{league_id}.{EXTENSION}"
        full_path_object = self.repo.get_full_path(filename)

        if not full_path_object.exists():
            return None

        model = xgb.Booster()
        model.load_model(str(full_path_object))
        logger.info(">> Model XGBOOST loaded - name:{filename}")
        return model