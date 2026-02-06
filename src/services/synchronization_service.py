from datetime import datetime
from dataclasses import asdict
from typing import Optional
from src.domain.entities import Synchronization
from src.di.ports.synchronization_port import SynchronizationPort
from src.di.ports.adapters.json_file_repository_port import (
    JsonFileRepositoryPort,
)
EXTENSION = "json"

class SynchronizationService(SynchronizationPort):
    def __init__(self, repo: JsonFileRepositoryPort):
        self._repo = repo

    def get_synchronization(self) -> Optional[Synchronization]:
        filename = f"sync.{EXTENSION}"
        data = self._repo.load(filename)

        if data is None:
            return None

        last_sync_date = data.get("last_sync_date")
        if isinstance(last_sync_date, str) and last_sync_date:
            data["last_sync_date"] = datetime.fromisoformat(last_sync_date)

        return Synchronization(**data)

    def save_synchronization(self, synchronization: Synchronization) -> None:
        filename = f"sync.{EXTENSION}"

        payload = asdict(synchronization)

        if isinstance(payload.get("last_sync_date"), datetime):
            payload["last_sync_date"] = payload["last_sync_date"].isoformat()

        self._repo.save(filename=filename, data=payload)
