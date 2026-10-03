"""Runtime data-path helpers for source and frozen builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_DATA_DIR_ENV = "DISK_ORGANISER_DATA_DIR"
_APP_DIR_NAME = "Disk Organiser"


def _source_backend_dir() -> Path:
    return Path(__file__).resolve().parent


def _frozen_data_dir() -> Path:
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / _APP_DIR_NAME
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        return Path(root).expanduser() / _APP_DIR_NAME if root else home / _APP_DIR_NAME
    root = os.environ.get("XDG_DATA_HOME")
    if root:
        return Path(root).expanduser() / "disk-organiser"
    return home / ".local" / "share" / "disk-organiser"


def data_dir() -> Path:
    """Return the writable directory for mutable application state.

    Source/development mode preserves the historical backend-local paths.
    Frozen builds move mutable state out of the temporary application bundle.
    ``DISK_ORGANISER_DATA_DIR`` overrides both for packaging/tests/operators.
    """
    override = os.environ.get(_DATA_DIR_ENV)
    if override:
        path = Path(override).expanduser()
    elif bool(getattr(sys, "frozen", False)):
        path = _frozen_data_dir()
    else:
        return _source_backend_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_path(filename: str) -> str:
    """Return a path for one mutable application-state file/directory."""
    return str(data_dir() / filename)
