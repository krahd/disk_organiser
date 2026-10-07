"""One-shot metadata observation for a cooperatively selected directory.

This process-local lifecycle helper is not an OS permission grant or a durable
identity proof. No route, store, executor or provider is connected to it.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
import posixpath
import stat
import threading

from backend import disk_model as model


class SelectionError(ValueError):
    """The selection cannot be used for this operation."""


_FACTORY = object()
_LIMITS = model.ScanLimits(max_entries=2000, max_directory_entries=500,
                           max_depth=8, max_seconds=5, hash_files=False,
                           cross_filesystems=False)


def _generic_path(path):
    if type(path) is not str or not 1 <= len(path) <= 4096:
        raise SelectionError("Choose one bounded directory path")
    try:
        encoded = path.encode("utf-8", "strict")
    except UnicodeError as error:
        raise SelectionError("Use a valid UTF-8 directory path") from error
    if len(encoded) > 4096 or any(ord(char) < 32 or ord(char) == 127 for char in path):
        raise SelectionError("Use a bounded path without control characters")


def _posix_path(path):
    if (not path.startswith("/") or path == "/" or "//" in path
            or "\\" in path or path.endswith("/")
            or any(part in (".", "..") for part in path.split("/"))
            or posixpath.normpath(path) != path):
        raise SelectionError("Choose one direct absolute project directory")


def _same_directory(first, second):
    a, b = os.fstat(first), os.fstat(second)
    return (stat.S_ISDIR(a.st_mode) and stat.S_ISDIR(b.st_mode)
            and (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino))


class ReadOnlySelection:
    """A non-persistent, non-copyable selection created only by select_root."""
    __slots__ = ("_pid", "_lock", "_path", "_fd", "_state", "_active",
                 "_generation", "_revoked", "_cancelled", "_changed",
                 "_unsupported", "_failed")

    def __init__(self, key, path, fd=None, initial=None):
        if key is not _FACTORY:
            raise SelectionError("Use select_root to create a selection")
        self._pid = os.getpid()
        self._lock = threading.RLock()
        self._path, self._fd = path, fd
        self._state = "unavailable" if initial else "granted"
        self._active = False
        self._generation = 0
        self._revoked = self._cancelled = self._changed = False
        self._unsupported = initial == "unsupported"
        self._failed = initial == "failed"

    def _check_process(self):
        # Never touch a potentially inherited lock or descriptor in a fork copy.
        if getattr(self, "_pid", None) != os.getpid():
            raise SelectionError("Selection belongs to another process")

    @contextmanager
    def _locked(self):
        self._check_process()
        with self._lock:
            yield

    @property
    def state(self):
        self._check_process()
        with self._locked():
            return self._state

    def _close_fd_locked(self):
        fd, self._fd = self._fd, None
        if fd is not None:
            os.close(fd)

    def revoke(self):
        self._check_process()
        with self._locked():
            self._revoked = True
            self._generation += 1
            self._state = "revoked"
            # The active observing call retains ownership until its finaliser.
            if not self._active:
                self._close_fd_locked()

    close = revoke

    def __enter__(self):
        self._check_process()
        with self._locked():
            if self._state not in ("granted", "unavailable"):
                raise SelectionError("Selection is no longer available")
        return self

    def __exit__(self, *_exception):
        self.close()

    def __repr__(self):
        return "<ReadOnlySelection process-local>"

    def __copy__(self):
        raise TypeError("Selections cannot be copied")

    def __deepcopy__(self, _memo):
        raise TypeError("Selections cannot be copied")

    def __reduce__(self):
        raise TypeError("Selections cannot be serialised")

    def __reduce_ex__(self, _protocol):
        raise TypeError("Selections cannot be serialised")


def select_root(path):
    """Select one explicit address; tests alone wire this API to owned fixtures."""
    _generic_path(path)
    if not model.traversal_supported():
        return ReadOnlySelection(_FACTORY, path, initial="unsupported")
    _posix_path(path)
    fd = None
    try:
        fd = model._open_root(path)
        os.set_inheritable(fd, False)
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("Selected object is not a directory")
        return ReadOnlySelection(_FACTORY, path, fd)
    except OSError:
        if fd is not None:
            os.close(fd)
        return ReadOnlySelection(_FACTORY, path, initial="failed")
    except BaseException:
        if fd is not None:
            os.close(fd)
        raise


def _result(outcome, inventory=None):
    return {
        "schema_version": "disk-administration-scoped-observation/v1",
        "state": outcome, "observation": inventory if outcome in ("observed", "partial") else None,
        "read_only": True, "executable": False, "execution_authority": None,
        "undo_available": False, "source_safe_to_erase": False,
        "live_backup_verified": False, "live_restore_verified": False,
        "evidence": {"physical_volume_identity": None, "authenticated_content_versions": None,
                     "dependency_coverage": "unknown", "required_copy_bytes": None,
                     "destination_capacity": None, "backup_configuration": None,
                     "independent_copy_count": None, "restore_satisfied": None},
    }


def observe_once(selection, *, cancel=None, progress=None):
    """Admit at most one metadata result; cancellation/revocation is cooperative."""
    if type(selection) is not ReadOnlySelection:
        raise SelectionError("Use a live process-local selection")
    selection._check_process()
    if ((cancel is not None and not callable(cancel))
            or (progress is not None and not callable(progress))):
        raise SelectionError("Callbacks must be callable")
    with selection._locked():
        if selection._state not in ("granted", "unavailable"):
            raise SelectionError("Selection is active, spent or revoked")
        if selection._state == "unavailable":
            selection._state = "spent"
            return _result("unsupported" if selection._unsupported else "failed")
        selection._active = True
        selection._state = "observing"
        selection._generation += 1
        generation = selection._generation

    def eligible_locked():
        return (selection._active and selection._generation == generation
                and not any((selection._revoked, selection._changed, selection._cancelled,
                             selection._unsupported, selection._failed)))

    def stop_requested():
        with selection._locked():
            if not eligible_locked():
                return True
            # Callback admission is linearised here; invocation is outside lock.
            admitted = cancel is not None
        if admitted:
            try:
                answer = cancel()
                if type(answer) is not bool:
                    raise TypeError("Cancellation must be Boolean")
            except Exception:
                with selection._locked():
                    selection._failed = True
            else:
                with selection._locked():
                    selection._cancelled |= answer
        with selection._locked():
            return not eligible_locked()

    def notify_progress(value):
        with selection._locked():
            if not eligible_locked() or progress is None:
                return
            payload = {key: value[key] for key in ("entries_observed", "hashed_bytes", "status")}
        try:
            progress(payload)
        except Exception:
            with selection._locked():
                selection._failed = True
        # Already-admitted callbacks may finish after revoke. No new one follows.
        with selection._locked():
            return eligible_locked()

    def address_matches(path, scanner_fd=None):
        with selection._locked():
            if not eligible_locked():
                return False
            if path != selection._path:
                selection._changed = True
                return False
        reopened = None
        try:
            # No-follow re-walk catches replacement after scanner-open, too.
            reopened = model._open_root(selection._path)
            with selection._locked():
                if not eligible_locked():
                    return False
                matches = (_same_directory(selection._fd, reopened)
                           and (scanner_fd is None or _same_directory(selection._fd, scanner_fd)))
                selection._changed |= not matches
                return matches and eligible_locked()
        except OSError:
            with selection._locked():
                selection._failed = True
            return False
        finally:
            if reopened is not None:
                os.close(reopened)

    inventory = None
    try:
        if not stop_requested():
            try:
                inventory = model.scan_storage([selection._path], limits=_LIMITS,
                                               previous=None, cancel=stop_requested,
                                               progress=notify_progress, root_guard=address_matches)
                roots = inventory["scan"]["roots"]
                with selection._locked():
                    if len(roots) != 1:
                        selection._failed = True
                    elif roots[0]["status"] == "stale":
                        selection._changed = True
                    elif roots[0]["status"] == "unsupported":
                        selection._unsupported = True
                    elif roots[0]["status"] != "observed":
                        selection._failed = True
                    if inventory["scan"]["status"] not in ("complete", "partial", "cancelled"):
                        selection._failed = True
                # Native names/metadata must still fit the canonical contract.
                # Do not normalise or silently drop unrepresentable observations.
                model.validate_inventory(inventory)
                address_matches(selection._path)
                # The scanner's final progress callback may request cancellation.
                stop_requested()
            except Exception:
                with selection._locked():
                    selection._failed = True
        with selection._locked():
            # Shared terminal admission point: revoke/close uses this same lock.
            outcome = ("revoked" if selection._revoked else
                       "root_changed" if selection._changed else
                       "cancelled" if selection._cancelled else
                       "unsupported" if selection._unsupported else
                       "failed" if selection._failed or inventory is None else
                       "partial" if inventory["scan"]["status"] == "partial" else
                       "observed" if inventory["scan"]["status"] == "complete" else "failed")
            selection._active = False
            selection._state = "revoked" if selection._revoked else "spent"
            selection._close_fd_locked()
            return _result(outcome, inventory)
    finally:
        with selection._locked():
            # Also retire the grant if a BaseException interrupted trusted code.
            selection._active = False
            if selection._state == "observing":
                selection._state = "spent"
            selection._close_fd_locked()
