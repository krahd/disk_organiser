"""Tests for the Modelito provider wrapper (simulation mode)."""

import os
import sys
from types import SimpleNamespace

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


def test_modelito_analyse_drive_uses_sdk_response(monkeypatch):
    responses = iter(
        [
            '[{"action_type":"move","source":"/tmp/a.txt","destination":"/tmp/Organised/a.txt","reason":"cluster","confidence":0.8,"group":"Semantic groups"}]'
        ]
    )

    class FakeClient:
        def __init__(self, provider, model=None, **kwargs):
            self.provider = provider
            self.model = model

        def summarize(self, messages, settings=None):
            return next(responses)

    fake_sdk = SimpleNamespace(
        Client=FakeClient,
        Message=lambda role, content: {"role": role, "content": content},
    )
    monkeypatch.setattr(modelito, "_load_sdk", lambda: fake_sdk)
    actions = modelito.analyse_drive(
        [{"path": "/tmp/a.txt", "root": "/tmp", "extension_group": "text"}],
        preferences={"ollama_model": "llama3.2:3b"},
    )
    assert actions and actions[0]["action_type"] == "move"
    assert actions[0]["destination"].endswith("Organised/a.txt")


def test_modelito_refine_actions_uses_sdk_response(monkeypatch):
    responses = iter(
        [
            '[{"action_type":"move","source":"/tmp/a.txt","destination":"/tmp/Downloads/a.txt","reason":"downloads requested","confidence":0.9,"group":"Semantic groups"}]'
        ]
    )

    class FakeClient:
        def __init__(self, provider, model=None, **kwargs):
            self.provider = provider
            self.model = model

        def summarize(self, messages, settings=None):
            return next(responses)

    fake_sdk = SimpleNamespace(
        Client=FakeClient,
        Message=lambda role, content: {"role": role, "content": content},
    )
    monkeypatch.setattr(modelito, "_load_sdk", lambda: fake_sdk)
    actions = modelito.refine_actions(
        "move to downloads instead",
        [{"action_type": "move", "source": "/tmp/a.txt", "destination": "/tmp/Organised/a.txt"}],
        [{"path": "/tmp/a.txt", "root": "/tmp", "extension_group": "text"}],
    )
    assert actions and actions[0]["destination"].endswith("Downloads/a.txt")
