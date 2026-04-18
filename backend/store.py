"""Simple configuration persistence for model and preferences."""

import json
import os

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


def save_config(data: dict):
    """Save configuration to disk, merging with existing values."""
    existing = load_config()
    existing.update(data)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
