"""Pure payload tests using inert streams; no app import or saved state."""

import io
import json
import math
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend import maintenance_payload as payload  # noqa: E402


class ReadOnce(io.BytesIO):
    def __init__(self, raw):
        super().__init__(raw)
        self.sizes = []

    def read(self, size=-1):
        self.sizes.append(size)
        assert self.sizes == [payload.MAX_BYTES + 1]
        return super().read(size)

    def write(self, *_args):
        raise AssertionError("Payload reader must not write")


def read(raw):
    stream = ReadOnce(raw)
    try:
        return payload.read_maintenance_payload(stream)
    finally:
        assert stream.sizes == [payload.MAX_BYTES + 1]
        assert stream.tell() == min(len(raw), payload.MAX_BYTES + 1)
        assert not stream.closed
        assert stream.getvalue() == raw


@pytest.mark.parametrize("size", [payload.MAX_BYTES - 1, payload.MAX_BYTES, payload.MAX_BYTES + 1])
def test_byte_limit(size):
    raw = b'"' + b"x" * (size - 2) + b'"'
    if size > payload.MAX_BYTES:
        with pytest.raises(ValueError, match="byte limit"):
            read(raw)
    else:
        assert read(raw) == "x" * (size - 2)


def test_overflow_rejected_before_decode_or_parse(monkeypatch):
    parser = Mock(side_effect=AssertionError("Oversize payload reached parser"))
    monkeypatch.setattr(payload.json, "loads", parser)
    # Invalid UTF-8 is deliberately after the cap; byte overflow wins.
    with pytest.raises(ValueError, match="byte limit"):
        read(b" " * payload.MAX_BYTES + b"\xff" + b"ignored")
    parser.assert_not_called()


def test_utf8_multibyte_value_at_exact_cap():
    value = "x" * (payload.MAX_BYTES - 5) + "雪"
    raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
    assert len(raw) == payload.MAX_BYTES
    assert read(raw) == value


@pytest.mark.parametrize("raw", [b'"\xff"', b'"\xc0\xaf"', b'"\xed\xa0\x80"', b'"\xe9', b'"\xe9\x9b'])
def test_invalid_or_truncated_utf8(raw):
    with pytest.raises(UnicodeDecodeError):
        read(raw)


def test_utf8_cut_at_byte_budget_is_overflow_not_decode_failure():
    raw = b'"' + b"x" * (payload.MAX_BYTES - 2) + "雪".encode() + b'"'
    with pytest.raises(ValueError, match="byte limit"):
        read(raw)


def test_incomplete_utf8_at_exact_cap():
    raw = b'"' + b"x" * (payload.MAX_BYTES - 3) + b"\xe9\x9b"
    assert len(raw) == payload.MAX_BYTES
    with pytest.raises(UnicodeDecodeError):
        read(raw)


def nested(depth, kind):
    text = "0"
    for level in range(depth):
        text = ('{"v":' + text + "}" if kind == "object"
                or (kind == "mixed" and level % 2) else "[" + text + "]")
    return text.encode()


@pytest.mark.parametrize("depth", [31, 32, 33])
@pytest.mark.parametrize("kind", ["array", "object", "mixed"])
def test_depth_boundaries(depth, kind):
    raw = nested(depth, kind)
    if depth > payload.MAX_DEPTH:
        with pytest.raises(ValueError, match="nesting limit"):
            read(raw)
    else:
        assert read(raw) == json.loads(raw)


def test_excess_depth_never_reaches_recursive_parser(monkeypatch):
    parser = Mock(side_effect=AssertionError("Deep payload reached parser"))
    monkeypatch.setattr(payload.json, "loads", parser)
    with pytest.raises(ValueError, match="nesting limit"):
        read(b"[" * 10000 + b"0" + b"]" * 10000)
    parser.assert_not_called()


@pytest.mark.parametrize("value", [
    "[" * 1000 + "}" * 1000,
    '\\"[\\\\\\"{}]"',
    "雪\n\t\x00 [ \" ] \\",
    {"[" * 40: '\\"}['},
])
def test_string_braces_and_escapes_do_not_count_as_nesting(value):
    assert read(json.dumps(value, ensure_ascii=False).encode()) == value


@pytest.mark.parametrize("slashes", range(1, 9))
def test_even_and_odd_backslash_runs_do_not_hide_real_depth(slashes):
    # json.dumps supplies the precise escaping, including escaped quotes.
    quoted = json.dumps("\\" * slashes + '"[')
    raw = ("[" * 32 + quoted + "]" * 32).encode()
    assert read(raw) == json.loads(raw)
    with pytest.raises(ValueError, match="nesting limit"):
        read(b"[" + raw + b"]")


@pytest.mark.parametrize("nodes", [4095, 4096, 4097])
def test_array_node_boundaries(nodes):
    raw = json.dumps([0] * (nodes - 1)).encode()
    if nodes > payload.MAX_NODES:
        with pytest.raises(ValueError, match="node limit"):
            read(raw)
    else:
        assert read(raw) == [0] * (nodes - 1)


@pytest.mark.parametrize("nodes", [4095, 4096, 4097])
def test_object_keys_values_and_containers_each_count_once(nodes):
    value = {str(i): 0 for i in range(2047)}  # root + 2047 keys + 2047 values
    value["0"] = [0] * (nodes - 4095) if nodes > 4095 else 0
    raw = json.dumps(value).encode()
    if nodes > payload.MAX_NODES:
        with pytest.raises(ValueError, match="node limit"):
            read(raw)
    else:
        assert read(raw) == value


@pytest.mark.parametrize("raw", [b"null", b"false", b"true", b"123", b"-1.25", b'"text"', b"[]", b"{}",
                                 b'{"a":1,"a":2}', b'"\\ud800"', b'"\\u96ea"', b"1e309"])
def test_successful_json_value_semantics_are_preserved(raw):
    assert read(raw) == json.loads(raw)


def test_nonfinite_values_keep_existing_decoder_semantics():
    assert math.isnan(read(b"NaN"))
    assert read(b"Infinity") == math.inf
    assert read(b"-Infinity") == -math.inf


def test_duplicate_keys_count_only_retained_parsed_value():
    raw = ("{" + ",".join('"a":0' for _ in range(5000)) + "}").encode()
    assert len(raw) < payload.MAX_BYTES
    assert read(raw) == {"a": 0}


@pytest.mark.parametrize("raw", [b"", b" ", b"{", b"[", b"[0", b'{"a":', b'"unfinished',
                                 b'"escape\\', b'{"a":0}\x00', b"[}", b"]", b"{}{}", b"[0,]",
                                 b'{"a":}', b"\xef\xbb\xbf{}", b'"control\x01"'])
def test_malformed_and_truncated_payloads_fail(raw):
    with pytest.raises(ValueError):
        read(raw)


def test_read_failure_is_not_retried():
    stream = Mock()
    stream.read.side_effect = OSError("inert read failure")
    with pytest.raises(OSError, match="inert read failure"):
        payload.read_maintenance_payload(stream)
    stream.read.assert_called_once_with(payload.MAX_BYTES + 1)
    stream.write.assert_not_called()


def test_import_is_independent_and_has_no_app_or_io_side_effects():
    # A separate interpreter prevents prior backend imports hiding coupling.
    script = r'''
import builtins, importlib.util, io, json, os, pathlib, socket, sqlite3, sys, threading
def forbidden(*args, **kwargs):
    raise AssertionError("Pure helper import attempted a side effect")
builtins.open = io.open = os.open = os.mkdir = forbidden
sqlite3.connect = socket.socket = threading.Thread.start = forbidden
spec = importlib.util.spec_from_file_location("standalone_maintenance", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert "backend.app" not in sys.modules
assert not any(name.startswith("backend.") for name in sys.modules)
assert module.read_maintenance_payload(io.BytesIO(b'{"status":"idle"}')) == {"status": "idle"}
'''
    result = subprocess.run([sys.executable, "-B", "-c", script, str(ROOT / "backend/maintenance_payload.py")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
