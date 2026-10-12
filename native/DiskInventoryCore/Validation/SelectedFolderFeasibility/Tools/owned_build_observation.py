"""Quarantined Stage-B filesystem observer; not called by Stage-A tests or CI.

The sole root capability is created here for a fresh macOS build directory.
There is no reopen-from-JSON/path factory, build/sign command or launch command.
Only files produced inside that owned capability can be inventoried/read.
"""
from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time

import probe_contract as pc
import xctestrun_binding as xb

_KEY = object()


def _stamp(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
            value.st_size, value.st_nlink, value.st_mtime_ns, value.st_ctime_ns)


def _check(check):
    if check is not None:
        check()


def _check_options(check):
    # Omit the seam entirely on the unchanged closed/default path.
    return {} if check is None else {"check": check}


def _error_record(error):
    return {"kind": type(error).__name__[:128], "message": str(error)[:512],
            "errno": error.errno if isinstance(error, OSError) and type(error.errno) is int else None}


class RetirementFailure(pc.Refusal):
    """Bounded independent cleanup evidence without losing the active error."""
    def __init__(self, message, original, failures, omitted=0):
        self.original = original
        self.cleanup_failures = tuple(failures[:256])
        self.omitted_cleanup_failure_count = omitted + max(0, len(failures) - 256)
        records = ([dict(operation=_error_record(original))] if original is not None else [])
        records.extend(dict(cleanup=record) for record in self.cleanup_failures)
        self.failures = tuple(json.dumps(row, sort_keys=True) for row in records)
        super().__init__(message)


@contextmanager
def _scan_entries(descriptor, *, check=None):
    _check(check)
    entries = os.scandir(descriptor)
    original = None
    try:
        _check(check)
        yield entries
    except BaseException as error:
        original = error
        raise
    finally:
        try:
            entries.close()
        except BaseException as cleanup:
            raise RetirementFailure("ambiguous enumeration retirement", original,
                                    [_error_record(cleanup)]) from (original or cleanup)


class _Descriptors:
    def __init__(self, *, check=None):
        self.owned = []
        self.failure = None
        self.failures = []
        self.omitted_failures = 0
        self.check = check

    def acquire(self, callback):
        _check(self.check)
        descriptor = callback()
        self.owned.append(descriptor)
        _check(self.check)
        return descriptor

    def retire(self, descriptor):
        pc.require(descriptor in self.owned, "unowned descriptor retirement")
        self.owned.remove(descriptor)
        try:
            os.close(descriptor)
        except BaseException as error:
            self.failure = self.failure or error
            if len(self.failures) < 256:
                self.failures.append(dict(_error_record(error), descriptor=descriptor))
            else:
                self.omitted_failures += 1

    def finish(self, original=None):
        # Retirement is independent of the expired work/finalisation budget.
        for descriptor in tuple(reversed(self.owned)):
            self.retire(descriptor)
        if self.failure is not None:
            raise RetirementFailure("ambiguous descriptor retirement", original,
                                    self.failures, self.omitted_failures) from (original or self.failure)

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        self.finish(error)  # Cleanup cannot replace the first operation failure.


class OwnedBuild:
    def __init__(self, key, path, descriptor, identity):
        pc.require(key is _KEY, "fresh owned build capability required")
        self.path, self._descriptor, self._identity = path, descriptor, identity
        self._closed = False
        self._products_identity = None
        self._results_identity = None
        self._captures_identity = None

    @classmethod
    def create(cls, *, check=None):
        pc.require(sys.platform == "darwin", "owned native build requires macOS")
        _check(check)
        path = tempfile.mkdtemp(prefix="disk-selection-build-", dir="/private/tmp")
        _check(check)
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            _check(check)
            value = os.fstat(descriptor)
            pc.require(stat.S_ISDIR(value.st_mode) and stat.S_IMODE(value.st_mode) == 0o700 and
                       value.st_uid == os.getuid(), "private created build root")
            _check(check)
            return cls(_KEY, path, descriptor, (value.st_dev, value.st_ino))
        except BaseException as original:
            try:
                os.close(descriptor)
            except BaseException as cleanup:
                raise RetirementFailure("ambiguous root creation retirement", original,
                                        [dict(_error_record(cleanup), descriptor=descriptor)]) from original
            raise

    def close(self):
        if self._closed:
            return
        self._closed = True
        descriptor, self._descriptor = self._descriptor, -1
        try:
            os.close(descriptor)
        except BaseException as error:
            raise RetirementFailure("ambiguous root retirement", None,
                                    [dict(_error_record(error), descriptor=descriptor)]) from error

    def __enter__(self):
        self._admit()
        return self

    def __exit__(self, kind, original, traceback):
        try:
            self.close()
        except RetirementFailure as cleanup:
            raise RetirementFailure(str(cleanup), original, cleanup.cleanup_failures,
                                    cleanup.omitted_cleanup_failure_count) from (original or cleanup)

    def __del__(self):
        # Best-effort abandonment cleanup cannot supply acceptance evidence.
        # close() retires the number before the syscall and never retries it.
        if getattr(self, "_closed", True) is False:
            try:
                self.close()
            except OSError:
                pass
            except pc.Refusal:
                pass

    def _admit(self):
        pc.require(not self._closed, "retired build root")
        value = os.fstat(self._descriptor)
        named = os.stat(self.path, follow_symlinks=False)
        pc.require((value.st_dev, value.st_ino) == self._identity == (named.st_dev, named.st_ino)
                   and stat.S_ISDIR(named.st_mode) and stat.S_IMODE(named.st_mode) == 0o700
                   and named.st_uid == os.getuid(), "build root replaced")

    @property
    def products_path(self):
        self._admit()
        return self.path + "/Products"

    def create_products_directory(self, *, check=None):
        _check(check)
        self._admit()
        _check(check)
        os.mkdir("Products", 0o700, dir_fd=self._descriptor)
        _check(check)
        value = os.stat("Products", dir_fd=self._descriptor, follow_symlinks=False)
        _check(check)
        self._products_identity = (value.st_dev, value.st_ino)

    def _products(self, ledger):
        self._admit()
        descriptor = ledger.acquire(lambda: os.open("Products", os.O_RDONLY | os.O_DIRECTORY |
                                                     os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=self._descriptor))
        value = os.fstat(descriptor)
        named = os.stat("Products", dir_fd=self._descriptor, follow_symlinks=False)
        pc.require(stat.S_ISDIR(value.st_mode) and value.st_uid == os.getuid(), "owned product directory")
        pc.require(self._products_identity is not None and
                   (value.st_dev, value.st_ino) == self._products_identity == (named.st_dev, named.st_ino),
                   "product directory replaced")
        return descriptor

    def read_configuration(self, relative, *, check=None):
        _check(check)
        pc.require(type(relative) is str and relative.endswith(".xctestrun") and
                   "/" not in relative and "\\" not in relative and relative not in (".", "..") and
                   0 < len(pc.utf8(relative)) <= 255, "single configuration leaf")
        with _Descriptors(check=check) as ledger:
            parent = self._products(ledger)
            fd = ledger.acquire(lambda: os.open(relative, os.O_RDONLY | os.O_NOFOLLOW |
                                                os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent))
            value = os.fstat(fd)
            pc.require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1 and
                       value.st_uid == os.getuid() and 0 < value.st_size <= xb.MAX_BYTES,
                       "configuration type or byte budget")
            data, attempts = bytearray(), 0
            while len(data) <= value.st_size:
                _check(check)
                attempts += 1
                pc.require(attempts <= 4096, "configuration read-attempt budget")
                try:
                    chunk = os.read(fd, min(65536, value.st_size + 1 - len(data)))
                except InterruptedError:
                    continue
                _check(check)
                if not chunk:
                    break
                data.extend(chunk)
            pc.require(len(data) == value.st_size and _stamp(value) == _stamp(os.fstat(fd)),
                       "configuration changed while read")
            _check(check)
            self._admit()
            _check(check)
            return bytes(data)

    def create_captures_directory(self, *, check=None):
        _check(check)
        self._admit()
        _check(check)
        os.mkdir("Captures", 0o700, dir_fd=self._descriptor)
        _check(check)
        value = os.stat("Captures", dir_fd=self._descriptor, follow_symlinks=False)
        _check(check)
        pc.require(stat.S_ISDIR(value.st_mode) and stat.S_IMODE(value.st_mode) == 0o700 and value.st_uid == os.getuid(),
                   "private capture directory")
        self._captures_identity = (value.st_dev, value.st_ino)
        return {"device": value.st_dev, "inode": value.st_ino}

    def _capture_directory(self, ledger):
        self._admit()
        fd = ledger.acquire(lambda: os.open("Captures", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                           dir_fd=self._descriptor))
        value = os.fstat(fd)
        named = os.stat("Captures", dir_fd=self._descriptor, follow_symlinks=False)
        pc.require(self._captures_identity is not None and
                   (value.st_dev, value.st_ino) == self._captures_identity == (named.st_dev, named.st_ino) and
                   stat.S_IMODE(value.st_mode) == 0o700 and value.st_uid == os.getuid(), "capture directory replaced")
        return fd

    def _result_directory(self, ledger):
        self._admit()
        fd = ledger.acquire(lambda: os.open("Results.xcresult", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                           dir_fd=self._descriptor))
        value = os.fstat(fd)
        named = os.stat("Results.xcresult", dir_fd=self._descriptor, follow_symlinks=False)
        pc.require(stat.S_ISDIR(value.st_mode) and value.st_uid == os.getuid() and
                   (value.st_dev, value.st_ino) == (named.st_dev, named.st_ino), "owned result directory")
        identity = (value.st_dev, value.st_ino)
        if self._results_identity is None:
            self._results_identity = identity
        pc.require(identity == self._results_identity, "result directory replaced")
        return fd

    def inventory(self, *, results=False, captures=False, check=None):
        _check(check)
        pc.require(type(results) is bool and type(captures) is bool and not (results and captures), "fixed result selector")
        rows, total, deadline = [], 0, time.monotonic() + 30
        with _Descriptors(check=check) as ledger:
            root = self._result_directory(ledger) if results else self._capture_directory(ledger) if captures else self._products(ledger)
            root_metadata = os.fstat(root)

            def budget():
                _check(check)
                pc.require(time.monotonic() <= deadline, "product observation time budget")

            def entry_budget():
                budget()
                pc.require(len(rows) < pc.MAX_ENTRIES, "product entry budget")

            def walk(fd, prefix, depth):
                nonlocal total
                budget()
                pc.require(depth <= 64, "product depth budget")
                initial = os.fstat(fd)
                pc.require(initial.st_dev == root_metadata.st_dev and initial.st_uid == os.getuid(),
                           "product filesystem or owner")
                entry_budget()
                rows.append({"path": prefix or ".", "kind": "directory", "mode": initial.st_mode,
                             "uid": initial.st_uid, "gid": initial.st_gid})
                # Streaming enumeration; no unbounded listdir/rglob before the cap.
                with _scan_entries(fd, check=check) as entries:
                    entries = iter(entries)
                    while True:
                        budget()
                        try:
                            entry = next(entries)
                        except StopIteration:
                            break
                        entry_budget()
                        name = entry.name
                        pc.require(type(name) is str and 0 < len(pc.utf8(name)) <= 255 and
                                   name not in (".", "..") and "/" not in name and "\\" not in name,
                                   "product leaf")
                        path = prefix + "/" + name if prefix else name
                        pc.require(len(pc.utf8(path)) <= 1024, "product path budget")
                        observed = os.stat(name, dir_fd=fd, follow_symlinks=False)
                        pc.require(observed.st_dev == root_metadata.st_dev and observed.st_uid == os.getuid(),
                                   "product member filesystem or owner")
                        common = {"path": path, "mode": observed.st_mode,
                                  "uid": observed.st_uid, "gid": observed.st_gid}
                        if stat.S_ISLNK(observed.st_mode):
                            target = os.readlink(name, dir_fd=fd)
                            pc.require(_stamp(observed) == _stamp(os.stat(name, dir_fd=fd, follow_symlinks=False)),
                                       "product link changed")
                            rows.append(dict(common, kind="symlink", target=target))
                        elif stat.S_ISDIR(observed.st_mode):
                            child = ledger.acquire(lambda: os.open(name, os.O_RDONLY | os.O_DIRECTORY |
                                                                  os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd))
                            pc.require(_stamp(observed) == _stamp(os.fstat(child)), "product directory changed")
                            walk(child, path, depth + 1)
                            ledger.retire(child)
                        elif stat.S_ISREG(observed.st_mode):
                            pc.require(observed.st_nlink == 1 and observed.st_size <= pc.MAX_FILE_BYTES,
                                       "product regular file budget")
                            total += observed.st_size
                            pc.require(total <= pc.MAX_TOTAL_BYTES, "product total byte budget")
                            child = ledger.acquire(lambda: os.open(name, os.O_RDONLY | os.O_NOFOLLOW |
                                                                  os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd))
                            pc.require(_stamp(observed) == _stamp(os.fstat(child)), "product file changed")
                            digest, count, attempts = hashlib.sha256(), 0, 0
                            while count <= observed.st_size:
                                budget(); attempts += 1
                                pc.require(attempts <= 131072, "product read-attempt budget")
                                try:
                                    data = os.read(child, min(65536, observed.st_size + 1 - count))
                                except InterruptedError:
                                    continue
                                budget()
                                if not data:
                                    break
                                count += len(data); digest.update(data)
                            pc.require(count == observed.st_size and _stamp(observed) == _stamp(os.fstat(child)),
                                       "product read changed")
                            ledger.retire(child)
                            rows.append(dict(common, kind="file", size=count, sha256=digest.hexdigest()))
                        else:
                            raise pc.Refusal("special product refused before open")
                budget()
                pc.require(_stamp(initial) == _stamp(os.fstat(fd)), "product directory changed during listing")

            walk(root, "", 0)
            _check(check)
            self._admit()
            _check(check)
        # Reuse the reviewed root/descendant and component-wise link contract.
        # There is no filesystem link resolution or second traversal algorithm.
        _check(check)
        pc.validate_inventory_claim(rows)
        _check(check)
        return tuple(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                     for row in sorted(rows, key=lambda row: row["path"].encode("utf-8")))


@dataclass(frozen=True)
class FrozenBuild:
    raw_configuration: bytes
    parsed_configuration: xb.ParsedConfiguration
    inventory: tuple[str, ...]
    products: tuple[str, str, str]
    driver_context: bytes


def freeze(workspace, configuration_name, expected_products, driver_context, *, check=None):
    _check(check)
    options = _check_options(check)
    pc.require(type(workspace) is OwnedBuild, "owned build capability required")
    context = bind_driver_context(workspace, configuration_name, driver_context)
    raw = workspace.read_configuration(configuration_name, **options)
    parsed = xb.parse(raw)
    context_value = pc.decode_claim(context, 65536)
    target = json.loads(parsed.complete_tree)["TestConfigurations"][0]["TestTargets"][0]
    pc.require(target["UITargetAppBundleIdentifier"] == context_value["observedHostSignature"]["identifier"],
               "configuration/signature identifier mismatch")
    pc.require(expected_products == ("Debug/OwnedFolderProbe.app", "Debug/SelectionProbeUITests-Runner.app",
                                    "Debug/SelectionProbeUITests-Runner.app/Contents/PlugIns/SelectionProbeUITests.xctest"),
               "fixed experiment products")
    xb.bind(parsed, raw, expected_products)
    inventory = workspace.inventory(**options)
    rows = {json.loads(row)["path"]: json.loads(row) for row in inventory}
    pc.require(all(path in rows and rows[path]["kind"] == "directory" for path in expected_products),
               "missing observed product")
    # The same raw file is re-read after inventory; changed configuration refuses.
    pc.require(workspace.read_configuration(configuration_name, **options) == raw, "configuration changed during freeze")
    _check(check)
    return FrozenBuild(raw, parsed, inventory, expected_products, context)


def verify_unchanged(workspace, expected, configuration_name, driver_context, *, check=None):
    pc.require(type(workspace) is OwnedBuild and type(expected) is FrozenBuild, "retained owned freeze required")
    candidate = freeze(workspace, configuration_name, expected.products, driver_context, **_check_options(check))
    pc.require(candidate == expected, "observed build changed")
    # No launch permit is returned. Observed signatures, exact driver context,
    # fixture sealing and the separately approved runtime are still required.


def bind_driver_context(workspace, configuration_name, data):
    """Bind the exact intended invocation and observations; never invoke it.

    Stage B must obtain these observations through the native observer and
    approved toolchain, rather than relabelling imported JSON as observed.
    Verification compares them with the separately retained reviewed freeze.
    """
    value = pc.decode_claim(data, 65536)
    pc.keys(value, {"schemaVersion", "sourceCommit", "fixtureSHA256", "buildRoot", "productsRoot",
                    "workingDirectory", "executable", "arguments", "environment", "toolchain",
                    "observedHostSignature", "fixtureRunID", "fixtureCaseID"})
    pc.require(type(value["schemaVersion"]) is int and value["schemaVersion"] == 1, "driver schema")
    for field, pattern in [("sourceCommit", r"[0-9a-f]{40}"), ("fixtureSHA256", r"[0-9a-f]{64}")]:
        pc.require(type(value[field]) is str and re.fullmatch(pattern, value[field]), "driver identity")
    for field in ("fixtureRunID", "fixtureCaseID"):
        pc.require(type(value[field]) is str and pc.UUID.fullmatch(value[field]), "driver fixture identity")
    pc.require(value["buildRoot"] == value["workingDirectory"] == workspace.path and
               value["productsRoot"] == workspace.products_path, "driver roots")
    executable = "/Applications/Xcode_16.4.app/Contents/Developer/usr/bin/xcodebuild"
    pc.require(value["executable"] == executable, "fixed reviewed driver")
    pc.require(value["arguments"] == ["test-without-building", "-xctestrun", workspace.products_path + "/" + configuration_name,
                                       "-destination", "platform=macOS", "-parallel-testing-enabled", "NO",
                                       "-resultBundlePath", workspace.path + "/Results.xcresult"], "exact no-rebuild invocation")
    env = value["environment"]
    pc.keys(env, {"PATH", "DEVELOPER_DIR", "HOME", "TMPDIR", "LANG", "LC_ALL"})
    pc.require(env["PATH"] == "/usr/bin:/bin:/usr/sbin:/sbin" and
               env["DEVELOPER_DIR"] == "/Applications/Xcode_16.4.app/Contents/Developer" and
               env["LANG"] == env["LC_ALL"] == "en_US.UTF-8", "driver environment")
    for name in ("HOME", "TMPDIR"):
        pc.require(type(env[name]) is str and env[name].startswith("/") and len(pc.utf8(env[name])) <= 1024 and
                   all(ord(c) >= 32 and ord(c) != 127 for c in env[name]), "driver home/temp")
    pc.require(value["toolchain"] == {"xcodeVersion": "16.4", "xcodeBuild": "16F6", "sdkVersion": "15.5",
                                     "swiftVersion": "6.1.2"}, "reviewed driver toolchain")
    signature = value["observedHostSignature"]
    pc.keys(signature, {"identifier", "executable", "cdhash", "entitlements", "valid"})
    pc.require(signature["valid"] is True and signature["identifier"] == pc.BUNDLE_PREFIX + value["fixtureCaseID"] and
               type(signature["cdhash"]) is str and re.fullmatch(r"[0-9a-f]{40,128}", signature["cdhash"]) and
               signature["executable"] == workspace.products_path + "/Debug/OwnedFolderProbe.app/Contents/MacOS/OwnedFolderProbe",
               "host signature observations")
    pc.keys(signature["entitlements"], {"com.apple.security.app-sandbox", "com.apple.security.files.user-selected.read-only"})
    pc.require(all(v is True for v in signature["entitlements"].values()), "two true host entitlements")
    return bytes(data)  # Whole exact context, including both home/temp values.


if __name__ == "__main__":
    raise SystemExit(2)
