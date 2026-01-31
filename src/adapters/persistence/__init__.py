# src/adapters/persistence/__init__.py
from .database import DatabaseContext  # <-- KROPKA JEST KLUCZOWA
from .json_repository import JsonFileRepository

__all__ = ["DatabaseContext", "JsonFileRepository"]
