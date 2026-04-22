"""Simple configuration persistence for model and preferences."""

import json
import os
import tempfile

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")


def load_config():
    """Load configuration from disk, returning sensible defaults on error."""
    if not os.path.exists(CONFIG_FILE):
        return {"model": "ollama", "preferences": {}}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"model": "ollama", "preferences": {}}


def save_config(data: dict, dry_run: bool = False):
    """Save configuration to disk, merging with existing values.

    If `dry_run` is True, do not write the file; instead return the
    merged configuration that would have been saved.
    """
    existing = load_config()
    existing.update(data)
    if dry_run:
        return existing
    # Write atomically to avoid partial/corrupt config files on crash.
    dirpath = os.path.dirname(CONFIG_FILE)
    os.makedirs(dirpath, exist_ok=True)
    fd = None
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix="config.", dir=dirpath, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, CONFIG_FILE)
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
    return existing
