from __future__ import annotations

import importlib
from pathlib import Path

from backend import runtime_paths


def test_source_mode_preserves_backend_local_data_dir(monkeypatch):
    monkeypatch.delenv("DISK_ORGANISER_DATA_DIR", raising=False)
    monkeypatch.delattr(runtime_paths.sys, "frozen", raising=False)
    assert runtime_paths.data_dir() == Path(runtime_paths.__file__).resolve().parent


def test_data_dir_override_is_created(monkeypatch, tmp_path):
    target = tmp_path / "state"
    monkeypatch.setenv("DISK_ORGANISER_DATA_DIR", str(target))
    assert runtime_paths.data_dir() == target
    assert target.is_dir()
    assert runtime_paths.data_path("ops.db") == str(target / "ops.db")


def test_mutable_modules_honor_data_dir_override(monkeypatch, tmp_path):
    target = tmp_path / "runtime-state"
    monkeypatch.setenv("DISK_ORGANISER_DATA_DIR", str(target))

    from backend import op_store, scan_index, store

    importlib.reload(store)
    importlib.reload(op_store)
    importlib.reload(scan_index)

    assert store.CONFIG_FILE == str(target / "config.json")
    assert op_store.DB_FILE == str(target / "ops.db")
    assert op_store.BACKUP_ROOT == str(target / "ops_backups")
    assert scan_index.DB_FILE == str(target / "scan_index.db")
    assert (target / "ops.db").exists()
    assert (target / "scan_index.db").exists()
