import json
import os
from src.core import get_logger
from pathlib import Path
from typing import Any, Optional, Dict, Union

logger = get_logger(__name__) 

class JsonFileRepository:
    def __init__(self):
        self.storage_path = Path(os.getenv("STORAGE_DIR", "./data_storage"))
        self._ensure_directory_exists()

    def _ensure_directory_exists(self):
        if not self.storage_path.exists():
            try:
                self.storage_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created persistence directory: {self.storage_path}")
            except OSError as e:
                logger.error(f"Failed to create persistence directory {self.storage_path}: {e}")
                raise

    def get_full_path(self, filename: str) -> Path:
        return self.storage_path / filename

    def save(self, filename: str, data: Union[Dict, list]) -> None:
        target_path = self.get_full_path(filename)
        temp_path = target_path.with_suffix(f"{target_path.suffix}.tmp")

        try:
            # 1. Zapisz do pliku tymczasowego
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False, default=str)
                f.flush()
                os.fsync(f.fileno())

            # 2. Atomowa podmiana (rename jest operacją atomową w POSIX)
            os.replace(temp_path, target_path)
            logger.debug(f"Successfully saved JSON to {target_path}")

        except Exception as e:
            logger.error(f"Failed to save JSON file {filename}: {e}")
            if temp_path.exists():
                os.remove(temp_path)
            raise

    def load(self, filename: str) -> Optional[Union[Dict, list]]:
        target_path = self.get_full_path(filename)

        if not target_path.exists():
            logger.warning(f"File {filename} not found in {self.storage_path}")
            return None

        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted JSON file {filename}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            raise

    def delete(self, filename: str) -> bool:
        target_path = self.get_full_path(filename)
        try:
            if target_path.exists():
                os.remove(target_path)
                logger.info(f"Deleted file {filename}")
                return True
            return False
        except OSError as e:
            logger.error(f"Error deleting {filename}: {e}")
            return False