"""Tests for the Flask app endpoints.

These tests are integration-style and intentionally concise; allow missing
docstrings and unused pytest fixture arguments to reduce lint noise.
"""

# pylint: disable=missing-module-docstring,missing-function-docstring,unused-argument

import importlib
import os
import sys

# ensure repository root is on path so 'backend' package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

app = importlib.import_module("backend.app")


def test_root():
    client = app.app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("message")


def test_model_and_preferences_roundtrip(tmp_path, monkeypatch):
    client = app.app.test_client()
    # GET model
    r = client.get("/api/model")
    assert r.status_code == 200
    # POST model
    r2 = client.post("/api/model", json={"model": "test-model"})
    assert r2.status_code == 200
    j = r2.get_json()
    assert j.get("model") == "test-model"


def test_duplicates_and_visualisation(tmp_path):
    # create temporary files with duplicate content
    d = tmp_path / "scan"
    d.mkdir()
    f1 = d / "a.txt"
    f2 = d / "b.txt"
    content = b"hello world"
    f1.write_bytes(content)
    f2.write_bytes(content)
    client = app.app.test_client()
    r = client.post("/api/duplicates", json={"paths": [str(d)], "min_size": 1})
    assert r.status_code == 200
    j = r.get_json()
    assert isinstance(j.get("duplicates"), list)
    # visualisation
    r2 = client.post("/api/visualisation", json={"path": str(d), "depth": 1})
    assert r2.status_code == 200
    v = r2.get_json()
    assert "visualisation" in v


def test_validation_errors_return_400(tmp_path):
    client = app.app.test_client()
    d = tmp_path / "scan"
    d.mkdir()

    dup_resp = client.post("/api/duplicates", json={"paths": [str(d)], "min_size": -1})
    assert dup_resp.status_code == 400
    assert "min_size" in dup_resp.get_json().get("error", "")

    vis_resp = client.post("/api/visualisation", json={"path": str(d), "depth": -1})
    assert vis_resp.status_code == 400
    assert "depth" in vis_resp.get_json().get("error", "")


def test_zero_values_are_allowed_for_min_size_and_depth(tmp_path):
    client = app.app.test_client()
    d = tmp_path / "scan"
    d.mkdir()
    (d / "a.txt").write_text("x", encoding="utf-8")

    dup_resp = client.post("/api/duplicates", json={"paths": [str(d)], "min_size": 0})
    assert dup_resp.status_code == 200

    vis_resp = client.post("/api/visualisation", json={"path": str(d), "depth": 0})
    assert vis_resp.status_code == 200


def test_scan_start_accepts_path_string(tmp_path):
    client = app.app.test_client()
    d = tmp_path / "scan"
    d.mkdir()
    f1 = d / "a.txt"
    f2 = d / "b.txt"
    content = b"same-content"
    f1.write_bytes(content)
    f2.write_bytes(content)

    start = client.post(
        "/api/scan/start",
        json={"path": str(d), "min_size": 1, "dry_run": True},
    )
    assert start.status_code == 200
    payload = start.get_json()
    assert payload.get("backend") == "thread"
    assert payload.get("dry_run") is True


def test_paths_validation_for_duplicates_and_scan_start(tmp_path):
    client = app.app.test_client()
    d = tmp_path / "scan"
    d.mkdir()

    bad_shape = client.post("/api/duplicates", json={"paths": {"x": str(d)}})
    assert bad_shape.status_code == 400
    assert "paths must be a list or string path" in bad_shape.get_json().get("error", "")

    bad_member = client.post("/api/scan/start", json={"paths": [str(d), 1], "dry_run": True})
    assert bad_member.status_code == 400
    assert "non-empty strings" in bad_member.get_json().get("error", "")
