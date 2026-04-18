"""Test asynchronous scan-index rebuild job and progress reporting."""

import importlib
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

app = importlib.import_module("backend.app")


def test_rebuild_async_reports_progress(tmp_path):
    # prepare a small tree of files
    d = tmp_path / "rebuild"
    d.mkdir()
    for i in range(3):
        (d / f"file{i}.txt").write_bytes(f"content-{i}".encode())

    client = app.app.test_client()
    r = client.post(
        "/api/scan_index/rebuild_async", json={"paths": [str(d)], "min_size": 1}
    )
    assert r.status_code == 200
    j = r.get_json()
    job_id = j.get("job_id")
    assert job_id

    # poll job status until finished (small timeout for CI)
    deadline = time.time() + 10
    status = None
    while time.time() < deadline:
        sr = client.get(f"/api/scan/status/{job_id}")
        assert sr.status_code == 200
        s = sr.get_json()
        if s.get("status") in ("finished", "failed", "cancelled"):
            status = s
            break
        time.sleep(0.25)

    assert status is not None
    assert status.get("status") == "finished"
    assert isinstance(status.get("result"), dict)
    assert status["result"].get("upserted", 0) >= 1
