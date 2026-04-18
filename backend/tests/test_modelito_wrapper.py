"""Tests for the Modelito provider wrapper (simulation mode)."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from backend.model_wrappers import modelito  # noqa: E402


def _sample_duplicates(tmp_path):
    d = tmp_path / "mclient"
    d.mkdir()
    a = d / "a.txt"
    b = d / "b.txt"
    a.write_bytes(b"1")
    b.write_bytes(b"1")
    return [
        {
            "hash": "h",
            "files": [{"path": str(a), "size": 1}, {"path": str(b), "size": 1}],
        }
    ]


def test_modelito_simulate(tmp_path, monkeypatch):
    monkeypatch.setenv("MODELITO_SIMULATE", "1")
    dups = _sample_duplicates(tmp_path)
    suggestions = modelito.suggest_organise(dups)
    assert suggestions and isinstance(suggestions, list)
    assert "provider" in suggestions[0] or "moves" in suggestions[0]
