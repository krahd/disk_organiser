import importlib
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

app = importlib.import_module("backend.app")


def _build_large_contexts(count: int = 600):
    return [
        {
            "path": f"/tmp/file_{idx}.txt",
            "size": idx + 1,
            "extension_group": "text",
            "probable_stale_reasons": [],
            "near_duplicate_key": f"g{idx % 10}",
            "near_duplicate_group_size": 2,
        }
        for idx in range(count)
    ]


def test_analyse_reason_handles_large_context_payload(monkeypatch, tmp_path):
    root = tmp_path / "analysis"
    root.mkdir(parents=True)

    # Keep this route-level test deterministic and fast.
    monkeypatch.setattr(app, "model_client", None)

    client = app.app.test_client()
    response = client.post(
        "/api/analyse/reason",
        json={
            "paths": [str(root)],
            "contexts": _build_large_contexts(600),
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    analysis_summary = payload["op"]["metadata"]["analysis_summary"]
    assert analysis_summary["file_count"] == 600
    assert analysis_summary["near_duplicate_clusters"] == 10
    assert isinstance(payload["actions"], list)
    assert payload["backup_status"] is not None
    assert "analysis_capabilities" in payload


@pytest.mark.parametrize(
    "request_json,expected_substring",
    [
        ({"paths": {"bad": "shape"}}, "paths must be a list or string path"),
        ({"paths": ["", "ok"]}, "non-empty strings"),
        ({"path": 123}, "paths must be a list or string path"),
        ({"paths": ["/tmp"], "max_files": "abc"}, "invalid literal for int()"),
    ],
)
def test_analyse_start_fuzzed_invalid_payloads_return_400(request_json, expected_substring):
    client = app.app.test_client()
    response = client.post("/api/analyse/start", json=request_json)

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"
    assert expected_substring in payload["error"]["message"]


def test_scan_cancel_rejects_missing_job_id():
    client = app.app.test_client()

    response = client.post("/api/scan/cancel", json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == "missing job_id"
