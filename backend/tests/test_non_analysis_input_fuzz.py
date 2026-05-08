import importlib
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

app = importlib.import_module("backend.app")


@pytest.mark.parametrize(
    "endpoint,body,expected_status,expected_error_substring",
    [
        (
            "/api/organise/preview",
            {"suggestions": {"bad": "shape"}},
            400,
            "missing suggestions",
        ),
        (
            "/api/organise/execute",
            {},
            400,
            "missing op_id",
        ),
        (
            "/api/organise/undo",
            {},
            400,
            "missing op_id",
        ),
        (
            "/api/chat",
            {"op_id": "", "message": "refine"},
            400,
            "op_id",
        ),
        (
            "/api/chat",
            {"op_id": "abc", "message": ""},
            400,
            "message",
        ),
        (
            "/api/model",
            {},
            400,
            "missing model",
        ),
        (
            "/api/recycle/delete_op",
            {},
            400,
            "missing op_id",
        ),
        (
            "/api/recycle/cleanup",
            {"retention_days": "not-a-number"},
            400,
            "invalid retention_days",
        ),
    ],
)
def test_non_analysis_routes_reject_malformed_payloads(
    endpoint, body, expected_status, expected_error_substring
):
    client = app.app.test_client()
    response = client.post(endpoint, json=body)

    assert response.status_code == expected_status
    payload = response.get_json()
    error = payload.get("error")
    if isinstance(error, dict):
        error_text = error.get("message") or error.get("error") or str(error)
    else:
        error_text = str(error)
    assert expected_error_substring in error_text


class _FakeScanIndex:
    @staticmethod
    def rebuild_index(paths, min_size=1, sample_size=4096, progress_callback=None):
        return {"ok": True, "paths": paths, "min_size": min_size, "sample_size": sample_size}

    @staticmethod
    def prune(retention_days=None, max_entries=None, dry_run=False):
        return {
            "ok": True,
            "retention_days": retention_days,
            "max_entries": max_entries,
            "dry_run": dry_run,
        }


class _FakeOllamaSDK:
    @staticmethod
    def start_ollama(host, port, timeout=10.0):
        return True

    @staticmethod
    def download_model(model_name, timeout=600.0):
        return True

    @staticmethod
    def serve_model(model_name=None, timeout=10.0):
        return True


@pytest.mark.parametrize(
    "endpoint,body,expected_error",
    [
        (
            "/api/scan_index/rebuild",
            {"min_size": "bad"},
            "invalid min_size",
        ),
        (
            "/api/scan_index/rebuild",
            {"sample_size": "bad"},
            "invalid sample_size",
        ),
        (
            "/api/scan_index/rebuild_async",
            {"min_size": "bad"},
            "invalid min_size",
        ),
        (
            "/api/scan_index/rebuild_async",
            {"sample_size": "bad"},
            "invalid sample_size",
        ),
        (
            "/api/maintenance/run",
            {"retention_days": "bad"},
            "invalid retention_days",
        ),
        (
            "/api/maintenance/run",
            {"max_entries": "bad"},
            "invalid max_entries",
        ),
    ],
)
def test_scan_index_and_maintenance_routes_validate_numeric_payloads(
    monkeypatch, endpoint, body, expected_error
):
    monkeypatch.setattr(app, "scan_index_mod", _FakeScanIndex)
    client = app.app.test_client()

    response = client.post(endpoint, json=body)
    assert response.status_code == 400
    payload = response.get_json()
    assert expected_error in str(payload.get("error"))


@pytest.mark.parametrize(
    "endpoint,body,expected_error",
    [
        (
            "/api/ollama/start",
            {"timeout": "bad"},
            "invalid timeout",
        ),
        (
            "/api/ollama/pull",
            {"model": "llama3.2:3b", "timeout": "bad"},
            "invalid timeout",
        ),
        (
            "/api/ollama/serve",
            {"model": "llama3.2:3b", "timeout": "bad"},
            "invalid timeout",
        ),
    ],
)
def test_ollama_write_routes_validate_timeout(monkeypatch, endpoint, body, expected_error):
    monkeypatch.setattr(app, "_load_modelito_sdk", lambda: _FakeOllamaSDK)
    client = app.app.test_client()

    response = client.post(endpoint, json=body)
    assert response.status_code == 400
    payload = response.get_json()
    error = payload.get("error")
    if isinstance(error, dict):
        error_text = error.get("message") or str(error)
    else:
        error_text = str(error)
    assert expected_error in error_text


def test_preferences_write_rejects_non_object_payload_shape():
    client = app.app.test_client()

    response = client.post("/api/preferences", json=["not", "an", "object"])
    assert response.status_code == 400
    assert "expected object" in str(response.get_json().get("error"))


def test_preferences_write_rejects_non_object_preferences_field():
    client = app.app.test_client()

    response = client.post("/api/preferences", json={"preferences": ["bad"]})
    assert response.status_code == 400
    assert "invalid preferences" in str(response.get_json().get("error"))
