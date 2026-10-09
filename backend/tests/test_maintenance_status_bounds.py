"""Route payload bounds using only owned temporary files and inert reads.

Run with a fresh owned DISK_ORGANISER_DATA_DIR before importing the app.
This is not a path-provenance, no-follow or blocking-open test suite.
"""

import builtins
import importlib
import json
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
api = importlib.import_module("backend.app")
from backend.maintenance_payload import MAX_BYTES  # noqa: E402

ERROR = {"error": "Unable to read maintenance status."}


@pytest.fixture
def owned_status(tmp_path, monkeypatch):
    path = tmp_path / "maintenance.json"
    path.write_bytes(b'{"status":"idle"}')
    monkeypatch.setattr(api, "MAINT_FILE", str(path))
    readers = []

    class OwnedReader:
        def __init__(self, stream):
            self.stream = stream
            self.read = Mock(wraps=stream.read)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def write(self, *_args):
            raise AssertionError("Status route must not write")

    def open_owned(candidate, mode):
        assert candidate == str(path)
        assert mode == "rb"
        reader = OwnedReader(builtins.open(candidate, mode))
        readers.append(reader)
        return reader

    opened = Mock(side_effect=open_owned)
    monkeypatch.setattr(api, "open", opened, raising=False)
    monkeypatch.setitem(api.app.config, "TESTING", True)
    yield api.app.test_client(), path, opened
    for reader in readers:
        reader.read.assert_called_once_with(MAX_BYTES + 1)
        assert reader.stream.closed


def assert_status(state, raw, expected_code):
    client, path, opened = state
    path.write_bytes(raw)
    # Unsupported body/query arguments must not change payload limits or scope.
    response = client.get("/api/maintenance/status?limit=999999&path=ignored&repair=true",
                          data=b'{"max_bytes":999999,"approved":true}',
                          content_type="application/json")
    assert response.status_code == expected_code
    expected = {"status": "ok", "maintenance": json.loads(raw)} if expected_code == 200 else ERROR
    assert response.get_json() == expected
    opened.assert_called_once_with(str(path), "rb")
    assert path.read_bytes() == raw
    if expected_code == 500:
        assert len(response.data) < 100


@pytest.mark.parametrize("size", [MAX_BYTES - 1, MAX_BYTES, MAX_BYTES + 1])
def test_route_byte_boundaries(owned_status, size):
    raw = b'"' + b"a" * (size - 2) + b'"'
    assert_status(owned_status, raw, 200 if size <= MAX_BYTES else 500)


@pytest.mark.parametrize("depth", [31, 32, 33])
def test_route_depth_boundaries(owned_status, depth):
    assert_status(owned_status, b"[" * depth + b"0" + b"]" * depth, 200 if depth <= 32 else 500)


@pytest.mark.parametrize("nodes", [4095, 4096, 4097])
def test_route_node_boundaries(owned_status, nodes):
    assert_status(owned_status, json.dumps([0] * (nodes - 1)).encode(), 200 if nodes <= 4096 else 500)


@pytest.mark.parametrize("raw", [b"null", b"true", b"42", b"[]", b"{}", b'{"a":1,"a":2}',
                                 b'"\\ud800"', b'"\\u96ea"', b'"[\\\\\\\"}]"'],
                         ids=lambda raw: f"value-{len(raw)}")
def test_route_success_values(owned_status, raw):
    assert_status(owned_status, raw, 200)


@pytest.mark.parametrize("raw", [b"{", b"\xff\xfe", b'"\xe9\x9b', b'"unfinished', b"[" * 10000,
                                 b'{}\x00', b"[}", b"{}{}"], ids=lambda raw: f"invalid-{len(raw)}")
def test_route_failed_payloads_are_bounded_and_unchanged(owned_status, raw):
    assert_status(owned_status, raw, 500)


def test_route_multibyte_value_at_byte_cap(owned_status):
    raw = ('"' + "x" * (MAX_BYTES - 5) + '雪"').encode()
    assert len(raw) == MAX_BYTES
    assert_status(owned_status, raw, 200)


def test_route_missing_stays_unknown_without_open_or_creation(owned_status):
    client, path, opened = owned_status
    path.unlink()
    response = client.get("/api/maintenance/status")
    assert response.status_code == 200
    assert response.get_json() == {"status": "unknown", "maintenance": None}
    opened.assert_not_called()
    assert not path.exists()


def test_route_open_failure_is_bounded_without_retry(owned_status):
    client, path, opened = owned_status
    original = path.read_bytes()
    opened.side_effect = OSError("private synthetic detail" * 10000)
    response = client.get("/api/maintenance/status")
    assert response.status_code == 500
    assert response.get_json() == ERROR
    assert len(response.data) < 100
    opened.assert_called_once_with(str(path), "rb")
    assert path.read_bytes() == original
