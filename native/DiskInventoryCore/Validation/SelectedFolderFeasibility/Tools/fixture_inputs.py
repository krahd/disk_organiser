"""Source for fresh owned Stage-B inputs; no build/sign/launch command.

Creation is separately gated runtime work and is not invoked by source tests.
The resulting JSON remains a claim until the separate native fixture proof.
"""
from dataclasses import dataclass
import hashlib
import errno
import json
import os
import re
import stat
import sys
import tempfile
import uuid

import probe_contract as pc
from owned_build_observation import (_Descriptors, _stamp, _check, _check_options,
                                     _error_record, RetirementFailure)


_FIXTURE_KEY = object()

class PreparedFixture:
    """Retained fresh-root capability, never reconstructed from a receipt/path."""
    def __init__(self, key, parent, claim, descriptor):
        pc.require(key is _FIXTURE_KEY, "fresh fixture capability required")
        self.parent, self.claim, self._descriptor = parent, bytes(claim), descriptor
        self._closed = False

    def close(self):
        if self._closed:
            return
        self._closed = True
        descriptor, self._descriptor = self._descriptor, -1
        try:
            os.close(descriptor)
        except BaseException as error:
            raise RetirementFailure("ambiguous fixture-root retirement", None,
                                    [dict(_error_record(error), descriptor=descriptor)]) from error

    def verify(self, *, check=None):
        _check(check)
        pc.require(not self._closed, "retired fixture capability")
        value = pc.decode_claim(self.claim, pc.FIXTURE_BYTES)
        expected = value["objects"]
        def match(metadata, row, directory=False):
            pc.require(all(getattr(metadata, "st_" + key) == row[field] for key, field in
                           [("dev", "device"), ("ino", "inode"), ("mode", "mode"), ("uid", "uid"), ("gid", "gid")]),
                       "fixture identity changed")
            if not directory:
                pc.require(metadata.st_nlink == 1 and metadata.st_size == row["size"] == 32, "fixture bytes/alias shape")
        match(os.fstat(self._descriptor), expected["parent"], True)
        match(os.stat(self.parent, follow_symlinks=False), expected["parent"], True)
        with _Descriptors(check=check) as ledger:
            for directory, leaf, key, data in [("selected", "probe.bin", "selectedFile", pc.SELECTED),
                                                ("outside", "sentinel.bin", "siblingFile", pc.SIBLING)]:
                _check(check)
                root = ledger.acquire(lambda: os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                                       dir_fd=self._descriptor))
                metadata = os.fstat(root)
                pc.require(stat.S_IMODE(metadata.st_mode) == 0o700 and metadata.st_uid == expected["parent"]["uid"] and
                           metadata.st_gid == expected["parent"]["gid"] and metadata.st_dev == expected["parent"]["device"],
                           "fixture child owner/type")
                if directory == "selected":
                    match(metadata, expected["selected"], True)
                    try:
                        os.stat("must-remain-absent.bin", dir_fd=root, follow_symlinks=False)
                    except FileNotFoundError as error:
                        pc.require(error.errno == errno.ENOENT, "absence errno")
                    else:
                        raise pc.Refusal("unexpected create evidence preserved")
                fd = ledger.acquire(lambda: os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=root))
                before = os.fstat(fd); match(before, expected[key])
                content = bytearray()
                for _ in range(64):
                    _check(check)
                    try:
                        block = os.read(fd, 33 - len(content))
                    except InterruptedError:
                        continue
                    _check(check)
                    if not block:
                        break
                    content.extend(block)
                    pc.require(len(content) <= 32, "fixture grew")
                pc.require(bytes(content) == data and _stamp(before) == _stamp(os.fstat(fd)), "fixture content changed")
                pc.require(_stamp(metadata) == _stamp(os.fstat(root)), "fixture child changed")
            _check(check)
            match(os.fstat(self._descriptor), expected["parent"], True)
            match(os.stat(self.parent, follow_symlinks=False), expected["parent"], True)
        _check(check)
        return hashlib.sha256(self.claim).hexdigest()

    def __del__(self):
        if getattr(self, "_closed", True) is False:
            try:
                self.close()
            except (OSError, pc.Refusal):
                pass  # Abandonment cleanup is not acceptance evidence.


def create_owned_fixture(*, check=None):
    pc.require(sys.platform == "darwin", "native fixture preparation requires macOS")
    _check(check)
    parent = tempfile.mkdtemp(prefix="disk-selection-owned-", dir="/private/tmp")
    # No automatic deletion or permission repair on any failure. The caller
    # must preserve/report this fresh owned preparation rather than retrying it.
    with _Descriptors(check=check) as ledger:
        root = ledger.acquire(lambda: os.open(parent, os.O_RDONLY | os.O_DIRECTORY |
                                              os.O_NOFOLLOW | os.O_CLOEXEC))
        initial = os.fstat(root)
        pc.require(stat.S_IMODE(initial.st_mode) == 0o700 and initial.st_uid == os.getuid(),
                   "created private fixture root")
        for directory in ("selected", "outside"):
            _check(check)
            os.mkdir(directory, 0o700, dir_fd=root)
        selected = ledger.acquire(lambda: os.open("selected", os.O_RDONLY | os.O_DIRECTORY |
                                                  os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=root))
        outside = ledger.acquire(lambda: os.open("outside", os.O_RDONLY | os.O_DIRECTORY |
                                                 os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=root))
        descriptors = {}
        for key, directory, name, data in [("selectedFile", selected, "probe.bin", pc.SELECTED),
                                           ("siblingFile", outside, "sentinel.bin", pc.SIBLING)]:
            _check(check)
            fd = ledger.acquire(lambda: os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL |
                                                os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                                                0o600, dir_fd=directory))
            written, attempts = 0, 0
            while written < len(data):
                _check(check)
                attempts += 1
                pc.require(attempts <= 64, "fixture write-attempt budget")
                try:
                    count = os.write(fd, data[written:])
                except InterruptedError:
                    continue
                _check(check)
                pc.require(count > 0, "fixture write made no progress")
                written += count
            _check(check)
            os.fsync(fd)
            _check(check)
            pc.require(os.pread(fd, 33, 0) == data, "same-descriptor fixture bytes")
            _check(check)
            descriptors[key] = fd
        objects = {}
        for key, fd in {"parent": root, "selected": selected, **descriptors}.items():
            _check(check)
            value = os.fstat(fd)
            pc.require(value.st_uid == initial.st_uid and value.st_gid == initial.st_gid and
                       value.st_dev == initial.st_dev, "fixture filesystem and owner")
            if stat.S_ISREG(value.st_mode):
                pc.require(value.st_nlink == 1, "fixture file alias")
            objects[key] = {"device": value.st_dev, "inode": value.st_ino, "mode": value.st_mode,
                            "uid": value.st_uid, "gid": value.st_gid, "size": value.st_size}
        run, case = str(uuid.uuid4()), str(uuid.uuid4())
        value = {"schemaVersion": 1, "runID": run, "caseID": case,
                 "bundleIdentifier": pc.BUNDLE_PREFIX + case,
                 "fixtureParent": parent, "selectedPath": parent + "/selected",
                 "selectedFile": parent + "/selected/probe.bin",
                 "siblingFile": parent + "/outside/sentinel.bin",
                 "absentPath": parent + "/selected/must-remain-absent.bin",
                 "objects": objects, "selectedBytesHex": pc.SELECTED.hex(),
                 "siblingBytesHex": pc.SIBLING.hex()}
        raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        _check(check)
        pc.parse_fixture_claim(raw)
        _check(check)
    # All source descriptors have retired before any build or possible launch.
    # Reacquire only this just-created root inside the creation operation. The
    # retained owner has no from-path/JSON constructor; CLOEXEC and close_fds
    # keep this capability out of the future host and test runner.
    _check(check)
    descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    owner = PreparedFixture(_FIXTURE_KEY, parent, raw, descriptor)
    try:
        owner.verify(**_check_options(check))
        _check(check)
        return owner
    except BaseException as original:
        try:
            owner.close()
        except RetirementFailure as cleanup:
            raise RetirementFailure("ambiguous fixture creation retirement", original,
                                    cleanup.cleanup_failures, cleanup.omitted_cleanup_failure_count) from original
        raise


def render_claimed_inputs(claim, source_commit, executable_path, capture_identity):
    """Pure generation from explicitly claimed bytes; supplies no execution permit."""
    admitted = pc.parse_fixture_claim(claim)
    value = pc.decode_claim(claim, pc.FIXTURE_BYTES)
    pc.require(type(source_commit) is str and re.fullmatch(r"[0-9a-f]{40}", source_commit), "source identity")
    pc.require(type(executable_path) is str and
               re.fullmatch(r"/private/tmp/disk-selection-build-[A-Za-z0-9_-]+/Products/Debug/OwnedFolderProbe.app/Contents/MacOS/OwnedFolderProbe", executable_path),
               "fixed owned executable coordinate")
    pc.require(re.fullmatch(r"/private/tmp/disk-selection-owned-[A-Za-z0-9_-]+", value["fixtureParent"]),
               "fixed owned fixture coordinate")
    pc.keys(capture_identity, {"device", "inode"})
    pc.require(all(type(x) is int and 0 < x < 2**63 for x in capture_identity.values()), "capture identity")
    build_root = executable_path.split("/Products/", 1)[0]
    fields = {"captureDirectory": build_root + "/Captures", "sourceCommit": source_commit, "fixtureSHA256": hashlib.sha256(claim).hexdigest(),
              "bundleIdentifier": admitted.bundle_identifier, "executablePath": executable_path,
              "selectedPath": value["selectedPath"]}
    # Every string is admitted ASCII from fixed identifiers/coordinates, so
    # JSON's quoted-string representation is also a literal Swift string here.
    pc.require(all(v.isascii() and '"' not in v and "\\" not in v for v in fields.values()),
               "literal generation shape")
    swift = "import Foundation\n\nenum ProbeSeal {\n" + "".join(
        "    static let " + key + " = " + json.dumps(item) + "\n" for key, item in fields.items()) + "    static let captureDevice: Int64 = " + str(capture_identity["device"]) + "\n" + \
            "    static let captureInode: UInt64 = " + str(capture_identity["inode"]) + "\n}\n"
    config = "OWNED_PROBE_IDENTIFIER = " + admitted.bundle_identifier + "\n"
    return {"Generated/ProbeSeal.swift": swift.encode(), "Generated/fixture.json": bytes(claim),
            "Generated/ProbeBuild.xcconfig": config.encode()}


if __name__ == "__main__":
    raise SystemExit(2)
