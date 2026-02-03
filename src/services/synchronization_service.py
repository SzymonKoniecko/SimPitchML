
from datetime import datetime
from dataclasses import asdict
from typing import Optional
from src.core import get_logger
from src.adapters.persistence.json_repository import JsonFileRepository
from src.adapters.grpc.client import simulation_engine
import json

from src.domain.entities import Synchronization

EXTENSION = "json"
logger = get_logger(__name__) 

class SynchronizationService:
    def __init__(self, repo: JsonFileRepository):
        self.repo = repo



    def get_synchronization(self) -> Optional[Synchronization]:
        filename = f"sync.{EXTENSION}"
        data = self.repo.load(filename)

        if data is None:
            return None

        last_sync_date = data.get("last_sync_date")
        if isinstance(last_sync_date, str) and last_sync_date:
            data["last_sync_date"] = datetime.fromisoformat(last_sync_date)

        return Synchronization(**data)

    def save_synchronization(self, synchronization: Synchronization) -> None:
        filename = f"sync.{EXTENSION}"

        payload = asdict(synchronization)

        # konwersja datetime -> ISO string (JSON-friendly)
        if isinstance(payload.get("last_sync_date"), datetime):
            payload["last_sync_date"] = payload["last_sync_date"].isoformat()

        self.repo.save(filename=filename, data=payload)