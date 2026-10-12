"""Bounded Stage-B data export; no build, signing, launch or source-owner close.

Only the disabled driver's reviewed admission may call this helper. A receipt
describes a closed historical packet, never a Stage-C capability or acceptance.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import os
import re
import stat
import sys
import tempfile
import time

import owned_build_observation as ob
import probe_contract as pc

MAX_BYTES = 64 * 1024 * 1024
MAX_FILES = 96
MAX_OUTCOME_BYTES = 1024 * 1024
MAX_MANIFEST_BYTES = 65536
MAX_ATTEMPTS = 4096
MAX_CONFIGURATIONS = 4
MAX_CONFIGURATION_BYTES = 1024 * 1024
MAX_CONFIGURATION_ENTRIES = 64
REPORT_PREFIX = "/private/tmp/disk-selection-report-"
_LEAF = re.compile(r"[a-z0-9][a-z0-9._-]{0,95}\Z")
_KEY = object()


def _error(label, error):
    return label + ":" + type(error).__name__ + ":" + str(error)[:1024]


def _budget(deadline):
    pc.require(type(deadline) in (int, float) and math.isfinite(deadline), "finite report deadline")
    pc.require(time.monotonic() < deadline, "report deadline exhausted")


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _read_bytes(descriptor, size, deadline):
    data = bytearray()
    for _ in range(MAX_ATTEMPTS):
        _budget(deadline)
        try:
            part = os.read(descriptor, min(65536, size + 1 - len(data)))
        except InterruptedError:
            continue
        pc.require(type(part) is bytes and len(part) <= min(65536, size + 1 - len(data)),
                   "bounded report read result")
        if not part:
            pc.require(len(data) == size, "short report read")
            return bytes(data)
        data.extend(part)
        pc.require(len(data) <= size, "report file grew during read")
    raise pc.Refusal("report read-attempt budget")


@dataclass(frozen=True)
class TerminalReceipt:
    path: str
    manifest_sha256: str
    manifest_bytes: int
    outcome: str
    root_device: int
    root_inode: int


class ReportFailure(pc.Refusal):
    def __init__(self, failures, *, path=None, close_disposition=None, receipt=None):
        self.failures = tuple(failures)
        self.receipt = receipt
        self.path = receipt.path if receipt is not None else path
        self.close_disposition = close_disposition
        super().__init__("; ".join(self.failures))


class Report:
    def __init__(self, key, path, descriptor, identity, deadline):
        pc.require(key is _KEY, "fresh owned report capability required")
        self.path, self._descriptor, self._identity = path, descriptor, identity
        self.deadline = deadline
        self._closed = self._finalising = False
        self._close_disposition = None
        self._names, self._rows, self._stamps = set(), {}, {}
        self._bytes, self._attempts = 0, 0
        self._failures = []

    @classmethod
    def create(cls, *, deadline):
        _budget(deadline)
        pc.require(sys.platform == "darwin", "owned report requires macOS")
        path = tempfile.mkdtemp(prefix="disk-selection-report-", dir="/private/tmp")
        pc.require(type(path) is str and re.fullmatch(re.escape(REPORT_PREFIX) + r"[A-Za-z0-9_-]{1,64}", path),
                   "fixed fresh report path")
        _budget(deadline)
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            value = os.fstat(descriptor)
            named = os.stat(path, follow_symlinks=False)
            pc.require(stat.S_ISDIR(value.st_mode) and stat.S_IMODE(value.st_mode) == 0o700 and
                       value.st_uid == os.getuid() and ob._stamp(value) == ob._stamp(named),
                       "private created report root")
            _budget(deadline)
            return cls(_KEY, path, descriptor, (value.st_dev, value.st_ino), deadline)
        except BaseException as error:
            failures = [_error("create", error)]
            disposition = {"status": "closed"}
            try:
                os.close(descriptor)
            except BaseException as closing:
                disposition = {"status": "unproved", "error": _error("report-close", closing)}
                failures.append(disposition["error"])
            raise ReportFailure(failures, close_disposition=disposition) from error

    def _admit(self):
        pc.require(not self._closed, "retired report root")
        _budget(self.deadline)
        held = os.fstat(self._descriptor)
        named = os.stat(self.path, follow_symlinks=False)
        pc.require((held.st_dev, held.st_ino) == self._identity and
                   ob._stamp(held) == ob._stamp(named) and stat.S_ISDIR(held.st_mode) and
                   stat.S_IMODE(held.st_mode) == 0o700 and held.st_uid == os.getuid(), "report root replaced")
        _budget(self.deadline)
        return held

    def add(self, name, data):
        pc.require(not self._finalising, "report finalisation already started")
        return self._add(name, data, final=False)

    def _add(self, name, data, *, final):
        descriptor = None
        failures = []
        row = stamp = None
        try:
            pc.require(self._attempts < MAX_FILES - (0 if final else 2), "report file-attempt budget")
            self._attempts += 1
            pc.require(type(name) is str and _LEAF.fullmatch(name) and name not in self._names,
                       "unique fixed report leaf")
            pc.require(final or name not in ("outcome.json", "manifest.json"), "reserved report leaf")
            pc.require(type(data) is bytes, "raw report bytes required")
            reserve = 0 if final else MAX_OUTCOME_BYTES + MAX_MANIFEST_BYTES
            pc.require(len(self._names) < MAX_FILES - (0 if final else 2) and
                       self._bytes + len(data) <= MAX_BYTES - reserve, "report packet budget")
            root = self._admit()
            # Count attempted exports conservatively, including partial failures.
            self._names.add(name)
            self._bytes += len(data)
            descriptor = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW |
                                 os.O_NONBLOCK | os.O_CLOEXEC, 0o600, dir_fd=self._descriptor)
            initial = os.fstat(descriptor)
            named = os.stat(name, dir_fd=self._descriptor, follow_symlinks=False)
            pc.require(stat.S_ISREG(initial.st_mode) and stat.S_IMODE(initial.st_mode) == 0o600 and
                       initial.st_uid == os.getuid() and initial.st_nlink == 1 and initial.st_size == 0 and
                       initial.st_dev == root.st_dev and ob._stamp(initial) == ob._stamp(named),
                       "fresh exclusive regular report file")
            offset = 0
            for _ in range(MAX_ATTEMPTS):
                if offset == len(data):
                    break
                _budget(self.deadline)
                chunk = data[offset:offset + 65536]
                try:
                    amount = os.write(descriptor, chunk)
                except InterruptedError:
                    continue
                pc.require(type(amount) is int and 0 < amount <= len(chunk), "report write progress")
                offset += amount
            pc.require(offset == len(data), "report write-attempt budget")
            written = os.fstat(descriptor)
            pc.require((initial.st_dev, initial.st_ino, initial.st_mode, initial.st_uid, initial.st_gid,
                        initial.st_nlink) == (written.st_dev, written.st_ino, written.st_mode, written.st_uid,
                                             written.st_gid, written.st_nlink) and written.st_size == len(data),
                       "report file changed during write")
            _budget(self.deadline)
            pc.require(os.lseek(descriptor, 0, os.SEEK_SET) == 0, "report readback position")
            actual = _read_bytes(descriptor, len(data), self.deadline)
            after = os.fstat(descriptor)
            named = os.stat(name, dir_fd=self._descriptor, follow_symlinks=False)
            pc.require(actual == data and ob._stamp(written) == ob._stamp(after) == ob._stamp(named),
                       "report file replaced or changed during readback")
            self._admit()
            row = {"path": name, "bytes": len(actual), "sha256": hashlib.sha256(actual).hexdigest()}
            stamp = ob._stamp(after)
        except BaseException as error:
            failures.append(_error("export", error))
        finally:
            if descriptor is not None:
                # Remove ownership before close: an ambiguous descriptor is never retried.
                retiring, descriptor = descriptor, None
                try:
                    os.close(retiring)
                except BaseException as error:
                    failures.append(_error("file-close", error))
        if failures:
            if len(self._failures) < MAX_FILES * 2:
                self._failures.extend(failures)
            raise ReportFailure(failures)
        self._rows[name], self._stamps[name] = row, stamp
        return dict(row)

    def _verify_packet(self):
        self._admit()
        pc.require(set(self._rows) == self._names and {"outcome.json", "manifest.json"} <= self._names,
                   "incomplete report packet")
        found = set()
        entries, failures = None, []
        try:
            entries = os.scandir(self._descriptor)
            for index, entry in enumerate(entries):
                _budget(self.deadline)
                pc.require(index < MAX_FILES and entry.name in self._stamps and entry.name not in found,
                           "unexpected report member")
                found.add(entry.name)
                named = os.stat(entry.name, dir_fd=self._descriptor, follow_symlinks=False)
                pc.require(ob._stamp(named) == self._stamps[entry.name], "report payload changed before close")
        except BaseException as error:
            failures.append(_error("packet-enumeration", error))
        finally:
            if entries is not None:
                retiring, entries = entries, None
                try:
                    retiring.close()
                except BaseException as error:
                    failures.append(_error("packet-enumeration-close", error))
        if failures:
            raise ReportFailure(failures)
        pc.require(found == self._names, "missing report member")
        self._admit()

    def abort(self):
        """Attempt the retained report close once, even after a deadline/failure."""
        if not self._closed:
            self._closed = True
            descriptor, self._descriptor = self._descriptor, -1
            self._close_disposition = {"status": "closed"}
            try:
                os.close(descriptor)
            except BaseException as error:
                self._close_disposition = {"status": "unproved", "error": _error("report-close", error)}
        return dict(self._close_disposition)

    def finalise(self, payload_outcome):
        pc.require(not self._finalising and not self._closed, "report finalisation is single-use")
        self._finalising = True
        failures = list(self._failures)
        manifest = None
        verified = False
        outcome = "failed"
        try:
            value = pc.decode_claim(payload_outcome, MAX_OUTCOME_BYTES)
            pc.require(type(value) is dict and value.get("outcome") in ("candidate_pass", "failed"),
                       "provisional report outcome required")
            if failures:
                value["outcome"] = "failed"
                payload_outcome = _json(value)
            outcome = value["outcome"]
            self._add("outcome.json", payload_outcome, final=True)
        except BaseException as error:
            failures.extend(error.failures if isinstance(error, ReportFailure) else (_error("outcome", error),))
        try:
            manifest = _json({"schemaVersion": 1, "files": [self._rows[name] for name in sorted(self._rows)]})
            pc.require(len(manifest) <= MAX_MANIFEST_BYTES, "report manifest budget")
            self._add("manifest.json", manifest, final=True)
        except BaseException as error:
            failures.extend(error.failures if isinstance(error, ReportFailure) else (_error("manifest", error),))
        try:
            self._verify_packet()
            verified = True
        except BaseException as error:
            failures.extend(error.failures if isinstance(error, ReportFailure) else (_error("packet", error),))
        disposition = self.abort()
        if disposition["status"] != "closed":
            failures.append(disposition["error"])
        try:
            _budget(self.deadline)
        except BaseException as error:
            failures.append(_error("final-close-deadline", error))
        receipt = None
        if verified and disposition["status"] == "closed":
            receipt = TerminalReceipt(self.path, hashlib.sha256(manifest).hexdigest(), len(manifest),
                                      "failed" if failures else outcome, *self._identity)
        if failures:
            raise ReportFailure(failures, close_disposition=disposition, receipt=receipt)
        return receipt


@dataclass(frozen=True)
class RawCapture:
    name: str
    data: bytes | None
    refusals: tuple[str, ...]


@dataclass(frozen=True)
class CaptureResult:
    captures: tuple[RawCapture, ...]
    failures: tuple[str, ...]


def _capture(workspace, parent, name, deadline):
    descriptor = None
    data, failures = None, []
    try:
        _budget(deadline)
        pc.require(type(name) is str and name.endswith(".xctestrun") and "/" not in name and
                   "\\" not in name and "\0" not in name and 0 < len(pc.utf8(name)) <= 255,
                   "single raw configuration leaf")
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        pc.require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_uid == os.getuid() and
                   before.st_dev == os.fstat(parent).st_dev and 0 <= before.st_size <= MAX_CONFIGURATION_BYTES,
                   "raw configuration type or byte budget")
        _budget(deadline)
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
        pc.require(ob._stamp(before) == ob._stamp(os.fstat(descriptor)), "raw configuration replaced before read")
        raw = _read_bytes(descriptor, before.st_size, deadline)
        pc.require(ob._stamp(before) == ob._stamp(os.fstat(descriptor)) ==
                   ob._stamp(os.stat(name, dir_fd=parent, follow_symlinks=False)),
                   "raw configuration replaced or changed during read")
        workspace._admit()
        data = raw
    except BaseException as error:
        failures.append(_error("configuration", error))
    finally:
        if descriptor is not None:
            retiring, descriptor = descriptor, None
            try:
                os.close(retiring)
            except BaseException as error:
                failures.append(_error("configuration-close", error))
    return RawCapture(name, data, tuple(failures))


def capture_configurations(workspace, *, deadline):
    """Capture ≤4 raw single leaves from the existing capability, without parsing.

    Global enumeration/parent-close failures do not erase individual results.
    No arbitrary path, configuration JSON or filesystem inventory is authority.
    """
    pc.require(type(workspace) is ob.OwnedBuild, "retained workspace capability required")
    ledger = ob._Descriptors()
    names, captures, failures = [], [], []
    parent = initial = entries = None
    try:
        _budget(deadline)
        parent = workspace._products(ledger)
        initial = os.fstat(parent)
        entries = os.scandir(parent)
        for index, entry in enumerate(entries):
            _budget(deadline)
            pc.require(index < MAX_CONFIGURATION_ENTRIES, "configuration enumeration budget")
            name = entry.name
            pc.require(type(name) is str, "configuration entry name")
            if name.endswith(".xctestrun"):
                pc.require(len(names) < MAX_CONFIGURATIONS, "raw configuration candidate budget")
                names.append(name)
        pc.require(names, "no raw configuration candidate")
    except BaseException as error:
        failures.append(_error("configuration-enumeration", error))
    finally:
        if entries is not None:
            retiring, entries = entries, None
            try:
                retiring.close()
            except BaseException as error:
                failures.append(_error("configuration-enumeration-close", error))
    if parent is not None:
        for name in names:
            captures.append(_capture(workspace, parent, name, deadline))
        try:
            _budget(deadline)
            workspace._admit()
            pc.require(ob._stamp(initial) == ob._stamp(os.fstat(parent)) ==
                       ob._stamp(os.stat("Products", dir_fd=workspace._descriptor, follow_symlinks=False)),
                       "raw configuration directory changed")
        except BaseException as error:
            failures.append(_error("configuration-parent", error))
    try:
        ledger.finish()
    except BaseException as error:
        failures.append(_error("configuration-parent-close", error))
    return CaptureResult(tuple(captures), tuple(failures))


if __name__ == "__main__":
    raise SystemExit(2)
