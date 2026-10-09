"""Bounded read/status request corpus; no request controls a filesystem path.

During request handling, operation/recycle stores are inert data mocks and only
an owned temporary maintenance file is read. Run with a fresh owned
DISK_ORGANISER_DATA_DIR before import (see docs/READ-STATUS-INPUT-FUZZ.md).
These checks do not exercise legacy storage traversal,
copy/recovery execution, a live provider, or any user directory.
"""

import builtins
from copy import deepcopy
import importlib
import io
import json
import os
import random
import sys
from unittest.mock import Mock
from urllib.parse import urlencode

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
api = importlib.import_module("backend.app")

ENDPOINTS = ("/api/ops", "/api/recycle/list", "/api/maintenance/status")
MAINTENANCE = {"timestamp": 1, "status": "idle"}
OPS = {"synthetic": {"id": "synthetic", "status": "preview"}}
RECYCLE = {"synthetic": {"metadata": {}, "files": [], "status": "preview"}}
EXPECTED = {
    "/api/ops": {"ops": OPS},
    "/api/recycle/list": {"recycle": RECYCLE},
    "/api/maintenance/status": {"status": "ok", "maintenance": MAINTENANCE},
}


@pytest.fixture
def read_client(tmp_path, monkeypatch):
    maintenance = tmp_path / "maintenance.json"
    maintenance.write_text(json.dumps(MAINTENANCE), encoding="utf-8")
    monkeypatch.setattr(api, "MAINT_FILE", str(maintenance))
    ops = Mock(return_value=deepcopy(OPS))
    recycle = Mock(return_value=deepcopy(RECYCLE))
    monkeypatch.setattr(api, "list_ops", ops)
    monkeypatch.setattr(api, "list_backups", recycle)
    forbidden = Mock(side_effect=AssertionError("read request reached an action"))
    for name in ("get_op", "create_op", "update_op", "undo_op", "delete_op",
                 "cleanup_recycle", "background_scan", "background_analyse",
                 "save_config", "_guided_store", "_load_modelito_sdk"):
        monkeypatch.setattr(api, name, forbidden)

    class ForbiddenBackend:
        def __getattr__(self, name):
            return forbidden(name)

        def __call__(self, *args, **kwargs):
            return forbidden(*args, **kwargs)

    monkeypatch.setattr(api, "model_client", ForbiddenBackend())

    def owned_read(path, mode="r", **kwargs):
        assert path == str(maintenance)
        assert mode == "r"
        return builtins.open(path, mode, **kwargs)

    opened = Mock(side_effect=owned_read)
    monkeypatch.setattr(api, "open", opened, raising=False)
    monkeypatch.setitem(api.app.config, "TESTING", True)
    yield api.app.test_client(), maintenance, ops, recycle, opened
    forbidden.assert_not_called()
    assert ops.return_value == OPS
    assert recycle.return_value == RECYCLE


def _assert_read(response, endpoint, state):
    assert response.status_code == 200
    assert response.get_json() == EXPECTED[endpoint]
    _, maintenance, ops, recycle, opened = state
    if endpoint == "/api/ops":
        ops.assert_called_once_with()
    else:
        ops.assert_not_called()
    if endpoint == "/api/recycle/list":
        recycle.assert_called_once_with()
    else:
        recycle.assert_not_called()
    if endpoint == "/api/maintenance/status":
        opened.assert_called_once_with(str(maintenance), "r", encoding="utf-8")
    else:
        opened.assert_not_called()
    assert maintenance.read_text(encoding="utf-8") == json.dumps(MAINTENANCE)


def _queries():
    # Unknown arguments have never been supported: preserve their inertness,
    # including fake pagination, traversal, action and cancellation arguments.
    cases = [
        "", "limit=-1&offset=NaN&page=Infinity", "limit=" + "9" * 8192,
        "path=..%2F..%2Fsynthetic&root=%00&backup_dir=C%3A%5Csynthetic",
        "limit=1&limit=2&limit%5B%5D=3&offset%5Bkey%5D=false",
        "dry_run=false&approved=true&cancel=true&delete=true",
        "path=%FF%FE%C0%AF&x=%&x=%ZZ&x=%252e%252e%252f",
        "path=" + "%61" * 16384,
        "&".join("path=synthetic" for _ in range(1024)),
    ]
    rng = random.Random(20261009)
    atoms = ["", "null", "[]", "{}", "true", "-1", "1e309", "../synthetic",
             "\\synthetic", "\x00", "é", "雪", "\u202e", "';--", "<script>"]
    for _ in range(48):
        cases.append(urlencode([(rng.choice(["path", "root", "limit", "page", "cancel"]),
                                 rng.choice(atoms)) for _ in range(rng.randrange(1, 12))]))
    return cases


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("query", _queries(), ids=lambda query: f"query-{len(query)}")
def test_query_corpus_never_changes_read_scope(read_client, endpoint, query):
    _assert_read(read_client[0].get(endpoint + "?" + query), endpoint, read_client)


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("body", [b"", b"null", b"false", b"123", b'"text"', b"[]", b"{}",
                                  b'{"path":"../synthetic","cancel":true}',
                                  b"{", b"\xff\xfe", b"[" * 2048,
                                  b'{"path":"' + b"a" * 65536 + b'"}'], ids=lambda body: f"body-{len(body)}")
def test_get_bodies_are_not_parsed_or_applied(read_client, endpoint, body):
    _assert_read(read_client[0].get(endpoint, data=body, content_type="application/json"),
                 endpoint, read_client)


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_get_does_not_consume_an_interrupted_body(read_client, endpoint):
    class InterruptedInput(io.BytesIO):
        def read(self, *_args, **_kwargs):
            raise AssertionError("GET consumed request input")

        readinto = read

    response = read_client[0].get(endpoint, environ_overrides={
        "wsgi.input": InterruptedInput(b"unfinished"), "CONTENT_LENGTH": "99999",
        "CONTENT_TYPE": "application/json",
    })
    _assert_read(response, endpoint, read_client)


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_early_response_close_does_not_change_later_reads(read_client, endpoint):
    for _ in range(3):
        response = read_client[0].get(endpoint, buffered=False)
        assert response.status_code == 200
        response.close()
    for mocked in read_client[2:]:
        mocked.reset_mock()
    _assert_read(read_client[0].get(endpoint), endpoint, read_client)


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_unsupported_methods_do_not_call_read_or_action_backends(read_client, endpoint, method):
    response = read_client[0].open(endpoint, method=method, json={"approved": True})
    assert response.status_code == 405
    for mocked in read_client[2:]:
        mocked.assert_not_called()


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("headers", [
    {"Host": "unrelated.example"}, {"Host": "localhost.unrelated.example"},
    {"Origin": "null"}, {"Origin": "https://unrelated.example"},
    {"Origin": "http://localhost:99"},
])
def test_remote_host_and_origin_rejected_before_read(read_client, endpoint, headers):
    assert read_client[0].get(endpoint, headers=headers).status_code == 403
    for mocked in read_client[2:]:
        mocked.assert_not_called()


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("host", ["[", "]", "[::1", "localhost]", "[not-ipv6]"])
def test_malformed_host_rejected_before_read(read_client, endpoint, host):
    # Override the WSGI environ so the test client does not parse the Host first.
    response = read_client[0].get(endpoint, environ_overrides={"HTTP_HOST": host})
    assert response.status_code == 403
    assert response.get_json() == {"error": "The filesystem API is available on localhost only."}
    for mocked in read_client[2:]:
        mocked.assert_not_called()


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("host", ["localhost", "localhost:5000", "127.0.0.1:5000", "[::1]:5000"])
def test_localhost_success_contract_unchanged(read_client, endpoint, host):
    _assert_read(read_client[0].get(endpoint, headers={"Host": host, "Origin": "http://" + host}),
                 endpoint, read_client)


@pytest.mark.parametrize("endpoint,index", [("/api/ops", 2), ("/api/recycle/list", 3)])
@pytest.mark.parametrize("error", [OSError("synthetic unavailable"), ValueError("synthetic corrupt data")])
def test_store_errors_retain_existing_json_error_contract(read_client, endpoint, index, error):
    read_client[index].side_effect = error
    response = read_client[0].get(endpoint)
    assert response.status_code == 500
    assert response.get_json() == {"error": str(error)}
    read_client[index].assert_called_once_with()
    read_client[4].assert_not_called()


def test_missing_maintenance_stays_unknown(read_client):
    read_client[1].unlink()
    response = read_client[0].get("/api/maintenance/status")
    assert response.status_code == 200
    assert response.get_json() == {"status": "unknown", "maintenance": None}
    read_client[4].assert_not_called()
    assert not read_client[1].exists()


@pytest.mark.parametrize("raw", [b"{", b"\xff\xfe", b'{"status": "idle"}\x00', b"[" * 2048],
                         ids=lambda raw: f"raw-{len(raw)}")
def test_malformed_maintenance_is_reported_without_rewrite(read_client, raw):
    read_client[1].write_bytes(raw)
    response = read_client[0].get("/api/maintenance/status")
    assert response.status_code == 500
    assert isinstance(response.get_json()["error"], str)
    assert read_client[1].read_bytes() == raw


def test_request_case_names_stay_bounded_for_windows(request):
    # Pytest exports each node ID as PYTEST_CURRENT_TEST. Do not expand the
    # large request corpus into Windows' size-limited environment variables.
    cases = [item for item in request.session.items if item.path == request.node.path]
    assert all(len(item.name) < 256 for item in cases)
