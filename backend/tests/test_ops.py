"""Tests for ops and background scan endpoints."""

# Tests often use short helper functions and fixtures; allow missing docstrings and
# larger helper functions without triggering pylint noise for tests.
# pylint: disable=missing-module-docstring,missing-function-docstring,too-many-locals

import importlib
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

app = importlib.import_module("backend.app")


def test_preview_execute_undo(tmp_path):
    d = tmp_path / "ops"
    d.mkdir()
    a = d / "a.txt"
    b = d / "b.txt"
    a.write_bytes(b"hello")
    b.write_bytes(b"hello")

    client = app.app.test_client()
    # get duplicates
    r = client.post("/api/duplicates", json={"paths": [str(d)], "min_size": 1})
    assert r.status_code == 200
    dup = r.get_json()
    assert dup.get("count") >= 1

    # compute suggestions
    sres = client.post("/api/organise", json={"duplicates": dup.get("duplicates")})
    assert sres.status_code == 200
    sj = sres.get_json()
    suggestions = sj.get("suggestions")
    assert suggestions

    # preview (create op)
    pres = client.post("/api/organise/preview", json={"suggestions": suggestions})
    assert pres.status_code == 200
    pj = pres.get_json()
    op = pj.get("op")
    assert op and op.get("id")

    # execute
    er = client.post("/api/organise/execute", json={"op_id": op.get("id")})
    assert er.status_code == 200
    ej = er.get_json()
    assert "executed" in ej

    # ensure files moved
    moved = ej["executed"][0]
    assert moved["status"] == "moved"

    # undo
    ur = client.post("/api/organise/undo", json={"op_id": op.get("id")})
    assert ur.status_code == 200
    uj = ur.get_json()
    assert "restored" in uj


def test_background_scan_thread(tmp_path):
    d = tmp_path / "scan"
    d.mkdir()
    (d / "x.txt").write_bytes(b"1")
    client = app.app.test_client()
    r = client.post("/api/scan/start", json={"paths": [str(d)], "min_size": 1})
    assert r.status_code == 200
    j = r.get_json()
    assert "job_id" in j
    job_id = j["job_id"]
    # poll for completion
    status = None
    for _ in range(20):
        s = client.get(f"/api/scan/status/{job_id}")
        sj = s.get_json()
        if sj.get("status") in ("finished", "failed"):
            status = sj
            break
        time.sleep(0.2)
    assert status is not None
    assert status.get("status") == "finished"

def test_execute_revalidates_paths_after_symlink_change(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    target = root / "target"
    root.mkdir()
    outside.mkdir()
    target.mkdir()
    source = root / "a.txt"
    source.write_text("hello", encoding="utf-8")
    destination = target / "a.txt"

    client = app.app.test_client()
    preview = client.post(
        "/api/organise/preview",
        json={
            "suggestions": [
                {
                    "action_type": "move",
                    "source": str(source),
                    "destination": str(destination),
                    "confidence": 1.0,
                }
            ],
            "metadata": {"user": "test", "paths": [str(root)]},
        },
    )
    assert preview.status_code == 200
    op_id = preview.get_json()["op"]["id"]

    target.rmdir()
    try:
        target.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        import pytest
        pytest.skip("symlinks unavailable in test environment")

    response = client.post("/api/organise/execute", json={"op_id": op_id})

    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "unsafe_operation"
    assert source.exists()
    assert not (outside / "a.txt").exists()
