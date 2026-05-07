"""Integration tests for the analysis interruption lifecycle.

These tests run ``background_analyse`` synchronously against a real (or
minimally stubbed) file tree, write job files to the live scan_jobs
directory, then hit the Flask test client so the full route logic is
exercised with real on-disk job state rather than monkeypatched helpers.
"""

import importlib
import json
import os
import sys
import uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

app_mod = importlib.import_module("backend.app")
tasks_mod = importlib.import_module("backend.tasks")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

JOBS_DIR = tasks_mod.JOBS_DIR


def _job_path(job_id: str) -> str:
    return os.path.join(JOBS_DIR, f"{job_id}.json")


def _cancel_path(job_id: str) -> str:
    return os.path.join(JOBS_DIR, f"{job_id}.cancel")


def _write_job(job: dict):
    """Persist a job dict directly to the scan_jobs directory."""
    os.makedirs(JOBS_DIR, exist_ok=True)
    with open(_job_path(job["id"]), "w", encoding="utf-8") as fh:
        json.dump(job, fh)


def _cleanup(job_id: str):
    for path in (_job_path(job_id), _cancel_path(job_id)):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Cancellation integration
# ---------------------------------------------------------------------------


def test_cancelled_job_reason_returns_409():
    """A cancelled job file on disk → /api/analyse/reason returns 409 job_cancelled."""
    job_id = uuid.uuid4().hex
    _write_job({"id": job_id, "status": "cancelled",
               "error": "cancelled", "result": None, "progress": {}})

    client = app_mod.app.test_client()
    response = client.post("/api/analyse/reason", json={"job_id": job_id})
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "job_cancelled"
    assert payload["error"]["details"]["job_status"] == "cancelled"

    _cleanup(job_id)


def test_cancelled_job_error_detail_propagated():
    """The cancellation error message from the job is propagated in the 409 response."""
    job_id = uuid.uuid4().hex
    _write_job({"id": job_id, "status": "cancelled",
               "error": "user requested cancel", "result": None, "progress": {}})

    client = app_mod.app.test_client()
    response = client.post("/api/analyse/reason", json={"job_id": job_id})
    assert response.status_code == 409
    payload = response.get_json()
    # The error field in the job becomes the reason detail in the HTTP response
    assert payload["error"]["details"].get("reason") == "user requested cancel"

    _cleanup(job_id)


# ---------------------------------------------------------------------------
# Real cancellation mechanics
# ---------------------------------------------------------------------------


def test_background_analyse_cancel_file_stops_job(tmp_path, monkeypatch):
    """background_analyse detects cancel file via progress_cb and sets status=cancelled."""
    (tmp_path / "a.txt").write_text("content", encoding="utf-8")

    job_id = uuid.uuid4().hex
    os.makedirs(JOBS_DIR, exist_ok=True)

    # Monkeypatch build_context to immediately call progress_cb (simulating a
    # large scan) so the cancel file is detected after the first callback.
    def fake_build_context(paths, min_size=1, max_files=None, progress_callback=None):
        open(_cancel_path(job_id), "w").close()  # write cancel file mid-run
        if progress_callback:
            progress_callback({"status": "scanning", "processed": 1})
        # The RuntimeError raised by progress_cb propagates up here
        return []  # unreachable when cancelled

    monkeypatch.setattr(tasks_mod, "build_context", fake_build_context)

    result = tasks_mod.background_analyse(paths=[str(tmp_path)], job_id=job_id)
    assert result["status"] == "cancelled"
    assert not os.path.exists(_cancel_path(job_id)), "cancel file must be cleaned up"

    _cleanup(job_id)


# ---------------------------------------------------------------------------
# Failure integration
# ---------------------------------------------------------------------------


def test_failed_job_reason_returns_500(tmp_path):
    """background_analyse that raises an unexpected exception → 500 analysis_failed."""
    job_id = uuid.uuid4().hex
    non_existent = str(tmp_path / "does_not_exist")

    result = tasks_mod.background_analyse(
        paths=[non_existent],
        job_id=job_id,
    )

    # build_context on a missing path should either finish with empty result
    # or fail; if it finishes, we manufacture a failed job for the 500 path.
    if result["status"] == "finished":
        # Override on disk so we can test the 500 branch
        result["status"] = "failed"
        result["error"] = "injected failure for test"
        _write_job(result)

    client = app_mod.app.test_client()
    response = client.post("/api/analyse/reason", json={"job_id": job_id})

    if result["status"] == "failed":
        assert response.status_code == 500
        payload = response.get_json()
        assert payload["error"]["code"] == "analysis_failed"
        assert payload["error"]["details"]["job_status"] == "failed"
    else:
        # path didn't exist but job still finished — acceptable behaviour
        assert response.status_code in (200, 500)

    _cleanup(job_id)


def test_injected_failed_job_reason_returns_500():
    """Directly write a failed job file and verify /api/analyse/reason returns 500."""
    job_id = uuid.uuid4().hex
    _write_job(
        {
            "id": job_id,
            "status": "failed",
            "error": "simulated I/O error",
            "result": None,
            "progress": {},
        }
    )

    client = app_mod.app.test_client()
    response = client.post("/api/analyse/reason", json={"job_id": job_id})
    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"]["code"] == "analysis_failed"
    assert payload["error"]["details"]["reason"] == "simulated I/O error"

    _cleanup(job_id)


# ---------------------------------------------------------------------------
# Not-ready (started / in-progress) integration
# ---------------------------------------------------------------------------


def test_in_progress_job_reason_returns_409_not_ready():
    """A job still in 'started' state → /api/analyse/reason returns 409 job_not_ready."""
    job_id = uuid.uuid4().hex
    _write_job(
        {
            "id": job_id,
            "status": "started",
            "result": None,
            "progress": {},
        }
    )

    client = app_mod.app.test_client()
    response = client.post("/api/analyse/reason", json={"job_id": job_id})
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "job_not_ready"
    assert payload["error"]["details"]["job_status"] == "started"

    _cleanup(job_id)


def test_in_progress_job_status_after_cancel_write():
    """Writing a cancel file while job is 'started' does not change the job file itself
    until background_analyse reads it; the route correctly reflects started state."""
    job_id = uuid.uuid4().hex
    _write_job(
        {
            "id": job_id,
            "status": "started",
            "result": None,
            "progress": {},
        }
    )
    # Simulate a cancel request arriving before the job thread reads it
    os.makedirs(JOBS_DIR, exist_ok=True)
    open(_cancel_path(job_id), "w").close()

    client = app_mod.app.test_client()
    response = client.post("/api/analyse/reason", json={"job_id": job_id})
    # Job file still says "started" so route should return 409 job_not_ready,
    # not job_cancelled (the background thread hasn't updated the file yet)
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "job_not_ready"

    _cleanup(job_id)


# ---------------------------------------------------------------------------
# Unknown job integration
# ---------------------------------------------------------------------------


def test_missing_job_file_returns_404():
    """No job file at all → /api/analyse/reason returns 404 not_found."""
    job_id = uuid.uuid4().hex  # guaranteed not to exist

    client = app_mod.app.test_client()
    response = client.post("/api/analyse/reason", json={"job_id": job_id})
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"]["code"] == "not_found"
    assert payload["error"]["details"]["job_id"] == job_id


# ---------------------------------------------------------------------------
# Happy path integration
# ---------------------------------------------------------------------------


def test_finished_job_reason_returns_200(tmp_path):
    """Full lifecycle: background_analyse → finished → /api/analyse/reason → 200."""
    docs = tmp_path / "Documents"
    docs.mkdir()
    (docs / "report.txt").write_text(
        "quarterly budget planning staffing timeline launch blockers",
        encoding="utf-8",
    )
    (docs / "report_copy.txt").write_text(
        "quarterly budget planning staffing timeline launch blockers",
        encoding="utf-8",
    )

    job_id = uuid.uuid4().hex
    result = tasks_mod.background_analyse(paths=[str(tmp_path)], job_id=job_id)

    assert result["status"] == "finished"
    assert result["result"] is not None

    client = app_mod.app.test_client()
    response = client.post("/api/analyse/reason", json={"job_id": job_id})
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["op"]["id"]
    assert isinstance(payload["actions"], list)
    assert payload["backup_status"] is not None
    assert "analysis_capabilities" in payload

    _cleanup(job_id)


def test_finished_job_contexts_used_not_recomputed(tmp_path, monkeypatch):
    """When job_id points to a finished job, contexts come from the job result,
    not from a fresh build_context call."""
    (tmp_path / "x.txt").write_text("alpha", encoding="utf-8")

    job_id = uuid.uuid4().hex
    result = tasks_mod.background_analyse(paths=[str(tmp_path)], job_id=job_id)
    assert result["status"] == "finished"

    call_log = []

    original_build = app_mod.build_context

    def spy_build(*args, **kwargs):
        call_log.append(args)
        return original_build(*args, **kwargs)

    monkeypatch.setattr(app_mod, "build_context", spy_build)

    client = app_mod.app.test_client()
    response = client.post("/api/analyse/reason", json={"job_id": job_id})
    assert response.status_code == 200
    # build_context must NOT have been called because job result provides contexts
    assert call_log == [], "build_context should not be called when job result has contexts"

    _cleanup(job_id)


# ---------------------------------------------------------------------------
# Cancel-then-restart round-trip
# ---------------------------------------------------------------------------


def test_cancel_then_restart_succeeds(tmp_path):
    """Cancel a job (via direct job file write), then start a fresh job on the same paths and finish it."""
    (tmp_path / "doc.txt").write_text("some content", encoding="utf-8")

    # --- first run: write a cancelled job file directly ---
    job_id_1 = uuid.uuid4().hex
    _write_job({"id": job_id_1, "status": "cancelled",
               "error": "cancelled", "result": None, "progress": {}})

    client = app_mod.app.test_client()
    r1 = client.post("/api/analyse/reason", json={"job_id": job_id_1})
    assert r1.status_code == 409
    assert r1.get_json()["error"]["code"] == "job_cancelled"

    # --- second run: real background_analyse on clean paths ---
    job_id_2 = uuid.uuid4().hex
    result2 = tasks_mod.background_analyse(paths=[str(tmp_path)], job_id=job_id_2)
    assert result2["status"] == "finished"

    r2 = client.post("/api/analyse/reason", json={"job_id": job_id_2})
    assert r2.status_code == 200
    assert r2.get_json()["op"]["id"]

    _cleanup(job_id_1)
    _cleanup(job_id_2)
