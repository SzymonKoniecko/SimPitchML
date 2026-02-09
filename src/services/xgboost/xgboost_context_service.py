from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import xgboost as xgb

from src.core import get_logger
from src.di.ports.adapters.json_file_repository_port import JsonFileRepositoryPort


logger = get_logger(__name__)

MODEL_EXT = "json"
META_EXT = "json"
META_PREFIX = "xgboost_meta"


@dataclass(frozen=True)
class XgboostArtifacts:
    model_home: Optional[xgb.XGBRegressor]
    model_away: Optional[xgb.XGBRegressor]
    feature_schema: Optional[List[str]]
    last_overview_created_date: Optional[str]


class XgBoostContextService:
    def __init__(self, repo: JsonFileRepositoryPort):
        self.repo = repo

    # ---------- filenames ----------

    def _model_filename(self, *, league_id: str, home_or_away: str) -> str:
        return f"xgboost_{home_or_away}_{league_id}.{MODEL_EXT}"

    def _meta_filename(self, *, league_id: str) -> str:
        return f"{META_PREFIX}_{league_id}.{META_EXT}"

    # ---------- metadata ----------

    def save_metadata(
        self,
        *,
        league_id: str,
        feature_schema: List[str],
        last_overview_created_date: Optional[str] = None,
    ) -> None:
        payload: Dict[str, Any] = {
            "league_id": league_id,
            "feature_schema": feature_schema,
            "last_overview_created_date": last_overview_created_date,
        }
        self.repo.save(filename=self._meta_filename(league_id=league_id), data=payload)
        logger.info(f">> XGBoost metadata saved: {self._meta_filename(league_id=league_id)}")

    def load_metadata(self, *, league_id: str) -> Optional[Dict[str, Any]]:
        meta = self.repo.load(self._meta_filename(league_id=league_id))
        if meta is None:
            return None
        if not isinstance(meta, dict):
            logger.warning(f">> Invalid metadata type: {type(meta)}")
            return None
        return meta

    # ---------- save/load single model ----------

    def save_league_model(
        self,
        *,
        model: xgb.XGBRegressor,
        home_or_away: str,
        league_id: str,
    ) -> None:
        filename = self._model_filename(league_id=league_id, home_or_away=home_or_away)
        full_path = self.repo.get_full_path(filename)
        model.save_model(str(full_path))
        logger.info(f">> XGBoost model ({home_or_away}) saved: {full_path}")

    def load_league_model(
        self,
        *,
        home_or_away: str,
        league_id: str,
    ) -> Optional[xgb.XGBRegressor]:
        filename = self._model_filename(league_id=league_id, home_or_away=home_or_away)
        full_path = self.repo.get_full_path(filename)

        if not full_path.exists():
            logger.info(f">> XGBoost model ({home_or_away}) not found: {full_path}")
            return None

        model = xgb.XGBRegressor()
        model.load_model(str(full_path))
        logger.info(f">> XGBoost model ({home_or_away}) loaded: {full_path}")
        return model

    # ---------- save/load both models + metadata ----------

    def save_league_models(
        self,
        *,
        league_id: str,
        model_home: xgb.XGBRegressor,
        model_away: xgb.XGBRegressor,
        feature_schema: List[str],
        last_overview_created_date: Optional[str] = None,
    ) -> None:
        self.save_league_model(model=model_home, home_or_away="home", league_id=league_id)
        self.save_league_model(model=model_away, home_or_away="away", league_id=league_id)

        self.save_metadata(
            league_id=league_id,
            feature_schema=feature_schema,
            last_overview_created_date=last_overview_created_date,
        )

    def load_league_models(self, *, league_id: str) -> XgboostArtifacts:
        model_home = self.load_league_model(home_or_away="home", league_id=league_id)
        model_away = self.load_league_model(home_or_away="away", league_id=league_id)

        meta = self.load_metadata(league_id=league_id) or {}
        raw_schema = meta.get("feature_schema")

        schema: Optional[List[str]] = None
        if isinstance(raw_schema, list) and all(isinstance(x, str) for x in raw_schema):
            schema = raw_schema

        last_overview_created_date = meta.get("last_overview_created_date")
        if not isinstance(last_overview_created_date, str):
            last_overview_created_date = None

        return XgboostArtifacts(
            model_home=model_home,
            model_away=model_away,
            feature_schema=schema,
            last_overview_created_date=last_overview_created_date,
        )
