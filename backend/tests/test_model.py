"""Tests for AI-assisted model suggestion endpoint."""

import importlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

app = importlib.import_module("backend.app")


def test_ai_suggest_endpoint(tmp_path):
    d = tmp_path / "ai"
    d.mkdir()
    f1 = d / "one.txt"
    f2 = d / "two.txt"
    content = b"sample content"
    f1.write_bytes(content)
    f2.write_bytes(content)

    client = app.app.test_client()
    # build duplicates payload
    r = client.post("/api/duplicates", json={"paths": [str(d)], "min_size": 1})
    assert r.status_code == 200
    j = r.get_json()
    dups = j.get("duplicates")
    assert dups

    s = client.post("/api/organise/suggest", json={"duplicates": dups})
    assert s.status_code == 200
    sj = s.get_json()
    assert "suggestions" in sj
    suggestions = sj["suggestions"]
    assert isinstance(suggestions, list)
    # ensure structure: keep and moves
    assert suggestions and "keep" in suggestions[0] and "moves" in suggestions[0]
