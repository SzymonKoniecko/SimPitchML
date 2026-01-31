import json
import os
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.adapters.persistence import JsonFileRepository

mock_logger = MagicMock()
sys.modules["src"] = MagicMock()
sys.modules["src.core"] = MagicMock()
sys.modules["src.core"].get_logger = MagicMock(return_value=mock_logger)


@pytest.fixture
def temp_storage(tmp_path, monkeypatch):
    env_dir = tmp_path / "test_data"
    monkeypatch.setenv("STORAGE_DIR", str(env_dir))
    return env_dir

@pytest.fixture
def repo(temp_storage):
    return JsonFileRepository()

# TESTs

class TestInitialization:
    def test_init_creates_directory_if_not_exists(self, temp_storage):
        assert not temp_storage.exists()
        JsonFileRepository()
        assert temp_storage.exists()

    def test_init_raises_error_on_permission_fail(self, temp_storage):
        # Symulujemy błąd przy tworzeniu katalogu
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                JsonFileRepository()

class TestSave:
    def test_save_creates_valid_json_file(self, repo, temp_storage):
        data = {"key": "value", "pl_chars": "zażółć gęślą jaźń"}
        filename = "test.json"
        
        repo.save(filename, data)
        
        file_path = temp_storage / filename
        assert file_path.exists()
        
        # Weryfikacja treści
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
        assert content == data

    def test_save_is_atomic_cleanup_on_fail(self, repo, temp_storage):
        data = {"a": 1}
        filename = "atomic.json"
        
        with patch("os.replace", side_effect=OSError("Disk full")):
            with pytest.raises(OSError):
                repo.save(filename, data)
        
        temp_files = list(temp_storage.glob("*.tmp"))
        assert len(temp_files) == 0, "Plik tymczasowy nie został usunięty po błędzie!"

class TestLoad:
    def test_load_returns_data_when_file_exists(self, repo, temp_storage):
        """Sprawdza poprawność odczytu istniejącego pliku."""
        filename = "data.json"
        expected_data = {"id": 123, "active": True}
        
        # Ręcznie tworzymy plik (arrange)
        target = temp_storage / filename
        with open(target, "w", encoding="utf-8") as f:
            json.dump(expected_data, f)
            
        # Act & Assert
        result = repo.load(filename)
        assert result == expected_data

    def test_load_returns_none_if_file_missing(self, repo):
        """Sprawdza, czy metoda zwraca None dla nieistniejącego pliku."""
        result = repo.load("ghost.json")
        assert result is None

    def test_load_raises_error_on_corrupted_json(self, repo, temp_storage):
        """Sprawdza, czy uszkodzony plik JSON powoduje rzucenie błędu."""
        filename = "broken.json"
        target = temp_storage / filename
        
        with open(target, "w", encoding="utf-8") as f:
            f.write('{"key": "value"') 
            
        with pytest.raises(json.JSONDecodeError):
            repo.load(filename)

class TestDelete:
    def test_delete_returns_true_and_removes_file(self, repo, temp_storage):
        """Sprawdza skuteczne usunięcie pliku."""
        
        filename = "to_delete.json"
        repo.save(filename, {})
        assert (temp_storage / filename).exists()
        
        result = repo.delete(filename)
        
        assert result is True
        assert not (temp_storage / filename).exists()

    def test_delete_returns_false_if_file_not_found(self, repo):
        result = repo.delete("non_existent.json")
        assert result is False

class TestPaths:
    def test_get_full_path_structure(self, repo, temp_storage):
        filename = "subdir/file.json"
        path = repo.get_full_path(filename)
        
        assert path == temp_storage / filename
        assert isinstance(path, Path)
