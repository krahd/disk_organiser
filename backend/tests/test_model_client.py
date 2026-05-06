"""Unit tests for backend.model_client.ModelClient."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from backend.model_client import ModelClient  # noqa: E402


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


def test_ci_dummy_provider(tmp_path):
    # explicit provider_name pointing to backend.model_wrappers.ci_dummy
    mc = ModelClient(provider_name="ci_dummy")
    dups = _sample_duplicates(tmp_path)
    suggestions = mc.suggest_organise(dups)
    assert suggestions and isinstance(suggestions, list)
    # provider should produce moves into AI_Duplicates
    moves = suggestions[0]["moves"]
    assert any("AI_Duplicates" in m["to"] for m in moves)


def test_reload_to_none_fallback(tmp_path):
    mc = ModelClient(provider_name="ci_dummy")
    dups = _sample_duplicates(tmp_path)
    assert mc.suggest_organise(dups)
    # reload to a missing provider module (fallback heuristic)
    mc.reload("missing_provider")
    sugg2 = mc.suggest_organise(dups)
    assert sugg2 and "AI_Duplicates" not in sugg2[0]["moves"][0]["to"]


def test_default_provider_is_modelito():
    mc = ModelClient()
    assert mc.provider_name == "modelito"


def test_refine_actions_filters_delete_stale_for_delete_nothing_phrase():
    mc = ModelClient(provider_name="missing_provider")
    refined = mc.refine_actions(
        "delete nothing from this proposal",
        [
            {"action_type": "delete_stale", "source": "/tmp/.DS_Store"},
            {"action_type": "move", "source": "/tmp/a.txt", "destination": "/tmp/Organised/a.txt"},
        ],
        [{"path": "/tmp/a.txt", "root": "/tmp"}],
    )
    assert all(action.get("action_type") != "delete_stale" for action in refined)
