"""Safety helpers: stale-file confidence and macOS backup checks."""

from __future__ import annotations

import platform
import shutil
import subprocess
import time
from typing import Dict, List


def stale_confidence(reasons: List[str]) -> float:
    weights = {
        "system-metadata": 1.0,
        "cache-or-build-artifact": 0.98,
        "old-installer-image": 0.95,
        "temporary-or-backup-suffix": 0.9,
        "zero-byte-file": 0.92,
        "cache-location": 0.9,
        "likely-manual-copy": 0.75,
    }
    if not reasons:
        return 0.0
    return max(weights.get(reason, 0.6) for reason in reasons)


def get_backup_status() -> Dict:
    status = {
        "platform": platform.system(),
        "available": False,
        "warning": None,
        "latest_backup": None,
        "snapshot_supported": False,
    }
    if platform.system() != "Darwin":
        status["warning"] = "Time Machine integration is only available on macOS"
        return status

    tmutil = shutil.which("tmutil")
    if not tmutil:
        status["warning"] = "tmutil not available"
        return status

    status["available"] = True
    status["snapshot_supported"] = True
    try:
        result = subprocess.run(
            [tmutil, "latestbackup"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        latest_backup = (result.stdout or "").strip()
        if latest_backup:
            status["latest_backup"] = latest_backup
        else:
            status["warning"] = (result.stderr or "No Time Machine backup found").strip()
    except Exception as exc:
        status["warning"] = str(exc)
    return status


def create_local_snapshot() -> Dict:
    if platform.system() != "Darwin":
        return {"created": False, "error": "local snapshots are only supported on macOS"}
    tmutil = shutil.which("tmutil")
    if not tmutil:
        return {"created": False, "error": "tmutil not available"}
    try:
        result = subprocess.run(
            [tmutil, "localsnapshot"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return {"created": True, "timestamp": time.time(), "output": (result.stdout or "").strip()}
        return {"created": False, "error": (result.stderr or result.stdout or "snapshot failed").strip()}
    except Exception as exc:
        return {"created": False, "error": str(exc)}