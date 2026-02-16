from datetime import datetime
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional
from src.domain.entities import Synchronization
from src.di.ports.synchronization_port import SynchronizationPort
from src.di.ports.adapters.json_file_repository_port import (
    JsonFileRepositoryPort,
)
EXTENSION = "json"

class SynchronizationService(SynchronizationPort):
    def __init__(self, repo: JsonFileRepositoryPort):
        self._repo = repo

    def get_synchronization(self) -> Optional[List[Synchronization]]:
        filename = f"sync.{EXTENSION}"
        data = self._repo.load(filename)

        if data is None:
            return None

        if not isinstance(data, list):
            raise TypeError(f"Expected list[dict] from repo.load, got {type(data).__name__}")

        result: List[Synchronization] = []
        for item in data:
            if not isinstance(item, dict):
                continue  # albo raise

            last_sync_date = item.get("last_sync_date")
            if isinstance(last_sync_date, str) and last_sync_date:
                item["last_sync_date"] = datetime.fromisoformat(last_sync_date)  # [web:404]

            result.append(Synchronization(**item))

        return result

    def save_synchronization(self, synchronization_list: List[Synchronization]) -> None:
        def _json_ready(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, list):
                return [_json_ready(x) for x in obj]
            if isinstance(obj, dict):
                return {k: _json_ready(v) for k, v in obj.items()}
            return obj
                
        filename = f"sync.{EXTENSION}"

        payload: List[Dict[str, Any]] = []
        for sync in synchronization_list:
            if not is_dataclass(sync):
                raise TypeError(f"Expected dataclass Synchronization, got {type(sync).__name__}")
            payload.append(_json_ready(asdict(sync)))

        self._repo.save(filename=filename, data=payload)