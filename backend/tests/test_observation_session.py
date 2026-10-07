"""Read-only observations use only directories and files this test creates."""
import copy
import json
import os
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend import disk_model as dm
from backend import observation_session as scope

POSIX = pytest.mark.skipif(not dm.traversal_supported(), reason="Descriptor-relative scope intentionally abstains")


def project(tmp_path):
    root = tmp_path / "selected"
    root.mkdir()
    (root / "notes.txt").write_text("owned non-critical fixture")
    (root / "Design").mkdir()
    (root / "Design" / "draft.txt").write_text("owned draft")
    return root


def assert_no_authority(result):
    assert result["read_only"] is True
    assert result["execution_authority"] is None
    for field in ("executable", "undo_available", "source_safe_to_erase", "live_backup_verified", "live_restore_verified"):
        assert result[field] is False
    assert result["evidence"]["dependency_coverage"] == "unknown"
    assert all(value is None for key, value in result["evidence"].items() if key != "dependency_coverage")


def assert_closed(fd):
    with pytest.raises(OSError):
        os.fstat(fd)


@pytest.mark.parametrize("value", [None, b"/owned", 1, True, [], {}, "", "/x\0y", "/x\ny", "/x\x7fy", "/\ud800", "/" + "x" * 4096, "/" + "é" * 2048])
def test_generic_input_bounds_reject_before_io(value, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("invalid input must not open anything")
    monkeypatch.setattr(dm, "_open_root", forbidden)
    with pytest.raises(scope.SelectionError):
        scope.select_root(value)


def test_pathlike_and_str_subclass_reject_without_conversion(monkeypatch):
    class PathLike:
        def __fspath__(self):
            raise AssertionError("must not call fspath")
    class Text(str):
        pass
    for value in (PathLike(), Text("/owned/project")):
        with pytest.raises(scope.SelectionError):
            scope.select_root(value)


@pytest.mark.parametrize("value", ["relative", "~", "/", "//", "///", "//owned/project", "/owned//project", "/owned/project/", "/owned/./project", "/owned/../project", "/owned/back\\slash"])
def test_posix_aliases_reject_before_open(value, monkeypatch):
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    monkeypatch.setattr(dm, "_open_root", lambda _path: pytest.fail("alias was opened"))
    with pytest.raises(scope.SelectionError):
        scope.select_root(value)


@pytest.mark.parametrize("value", ["/" + "x" * 4095, "/" + "é" * 2047 + "x", "/owned/Éclair"])
def test_exact_valid_encoding_edges_reach_only_selected_open(value, monkeypatch):
    seen = []
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    def unavailable(path):
        seen.append(path)
        raise PermissionError("owned boundary test")
    monkeypatch.setattr(dm, "_open_root", unavailable)
    result = scope.observe_once(scope.select_root(value))
    assert seen == [value]
    assert result["state"] == "failed" and result["observation"] is None


def test_unsupported_platform_abstains_without_io(monkeypatch):
    monkeypatch.setattr(dm, "traversal_supported", lambda: False)
    monkeypatch.setattr(dm, "_open_root", lambda _path: pytest.fail("unsupported open"))
    selection = scope.select_root("/owned/project")
    assert selection._fd is None
    result = scope.observe_once(selection)
    assert result["state"] == "unsupported" and result["observation"] is None
    assert_no_authority(result)
    with pytest.raises(scope.SelectionError):
        scope.observe_once(selection)


@POSIX
def test_metadata_only_one_shot_has_no_authority_or_content_reads(tmp_path, monkeypatch):
    root = project(tmp_path)
    selection = scope.select_root(str(root))
    held = selection._fd
    assert os.get_inheritable(held) is False
    real_open = os.open
    def directory_opens_only(path, flags, *args, **kwargs):
        assert flags & os.O_DIRECTORY and flags & os.O_NOFOLLOW
        assert flags & os.O_WRONLY == 0 and flags & os.O_RDWR == 0
        return real_open(path, flags, *args, **kwargs)
    monkeypatch.setattr(dm.os, "open", directory_opens_only)
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    result = scope.observe_once(selection)
    assert result["state"] == "observed"
    assert_no_authority(result)
    inventory = result["observation"]
    dm.validate_inventory(inventory)
    assert "synthetic" not in inventory
    assert inventory["scan"]["hash_policy"] == "metadata_only"
    assert inventory["scan"]["coverage"]["hashed_bytes"] == 0
    assert inventory["scan"]["limits"]["cross_filesystems"] is False
    assert all(entry["hash"]["status"] == "disabled" for entry in inventory["entries"])
    assert_closed(held)
    assert selection.state == "spent"
    with pytest.raises(scope.SelectionError):
        scope.observe_once(selection)


@POSIX
def test_selection_itself_never_enumerates_or_reads_contents(tmp_path, monkeypatch):
    root = project(tmp_path)
    monkeypatch.setattr(dm.os, "scandir", lambda *_args: pytest.fail("selection enumerated"))
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    with scope.select_root(str(root)) as selection:
        held = selection._fd
    assert_closed(held)


@POSIX
def test_root_and_ancestor_symlinks_and_nondirectory_fail_closed(tmp_path):
    root = project(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(root, target_is_directory=True)
    for path in (link, link / "Design", root / "notes.txt", tmp_path / "missing"):
        result = scope.observe_once(scope.select_root(str(path)))
        assert result["state"] == "failed" and result["observation"] is None
        assert_no_authority(result)


@POSIX
def test_child_symlink_and_known_placeholder_never_read_sentinel(tmp_path, monkeypatch):
    root = project(tmp_path)
    outside = tmp_path / "adjacent-owned-sentinel"
    outside.mkdir()
    (outside / "never-read.txt").write_text("owned sentinel")
    (root / "link").symlink_to(outside, target_is_directory=True)
    (root / "pending.icloud").write_text("owned placeholder marker")
    sentinel_inode = outside.stat().st_ino
    real_scandir = os.scandir
    def bounded_scan(fd):
        assert os.fstat(fd).st_ino != sentinel_inode
        return real_scandir(fd)
    monkeypatch.setattr(dm.os, "scandir", bounded_scan)
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    result = scope.observe_once(scope.select_root(str(root)))
    assert result["state"] == "partial"
    entries = {entry["relative_path"]: entry for entry in result["observation"]["entries"]}
    assert entries["link"]["status"] == "unsupported"
    assert entries["pending.icloud"]["hash"]["status"] == "placeholder_not_read"
    assert not any("never-read" in path for path in entries)


@POSIX
def test_revoke_before_start_closes_and_never_invokes_scanner(tmp_path, monkeypatch):
    selection = scope.select_root(str(project(tmp_path)))
    held = selection._fd
    selection.revoke()
    selection.revoke()
    assert_closed(held)
    monkeypatch.setattr(dm, "scan_storage", lambda *_args, **_kwargs: pytest.fail("revoked scan"))
    with pytest.raises(scope.SelectionError):
        scope.observe_once(selection)


@POSIX
def test_cancel_latches_transient_true_and_discards_inventory(tmp_path):
    selection = scope.select_root(str(project(tmp_path)))
    held = selection._fd
    answers = iter([False, False, True, False, False])
    result = scope.observe_once(selection, cancel=lambda: next(answers, False))
    assert result["state"] == "cancelled" and result["observation"] is None
    assert selection._cancelled is True
    assert_closed(held)


@POSIX
@pytest.mark.parametrize("answer", [None, 1, "yes", [], {}])
def test_non_boolean_cancel_is_failed_not_a_valid_result(tmp_path, answer):
    selection = scope.select_root(str(project(tmp_path)))
    held = selection._fd
    result = scope.observe_once(selection, cancel=lambda: answer)
    assert result["state"] == "failed" and result["observation"] is None
    assert_closed(held)


@POSIX
@pytest.mark.parametrize("kind", ["cancel", "progress"])
def test_callback_errors_close_resources_and_fail_closed(tmp_path, kind):
    selection = scope.select_root(str(project(tmp_path)))
    held = selection._fd
    def failure(*_args):
        raise RuntimeError("owned callback failure")
    result = scope.observe_once(selection, **{kind: failure})
    assert result["state"] == "failed" and result["observation"] is None
    assert_closed(held)


@POSIX
def test_final_progress_cancellation_is_polled_before_admission(tmp_path):
    selection = scope.select_root(str(project(tmp_path)))
    cancelled = False
    def progress(value):
        nonlocal cancelled
        if value["status"] == "complete":
            cancelled = True
    result = scope.observe_once(selection, cancel=lambda: cancelled, progress=progress)
    assert result["state"] == "cancelled" and result["observation"] is None


@POSIX
def test_progress_can_revoke_without_deadlock_or_late_inventory(tmp_path):
    selection = scope.select_root(str(project(tmp_path)))
    held = selection._fd
    progress_calls = []
    def progress(value):
        progress_calls.append(value)
        selection.revoke()
        assert os.fstat(held)  # Active observer owns it until terminal cleanup.
    result = scope.observe_once(selection, progress=progress)
    assert result["state"] == "revoked" and result["observation"] is None
    assert len(progress_calls) == 1
    assert set(progress_calls[0]) == {"entries_observed", "hashed_bytes", "status"}
    assert_closed(held)


@POSIX
def test_cancel_callback_may_revoke_and_revocation_takes_priority(tmp_path):
    selection = scope.select_root(str(project(tmp_path)))
    def cancel():
        selection.revoke()
        return True
    result = scope.observe_once(selection, cancel=cancel)
    assert result["state"] == "revoked" and result["observation"] is None


@POSIX
def test_selected_root_replaced_after_scanner_open_before_guard_is_rejected(tmp_path, monkeypatch):
    root = project(tmp_path)
    old = tmp_path / "old-owned-project"
    selection = scope.select_root(str(root))
    real_open = dm._open_root
    replaced = False
    def replace_after_open(path):
        nonlocal replaced
        fd = real_open(path)
        if not replaced:
            replaced = True
            root.rename(old)
            root.mkdir()
            (root / "never-enumerate.txt").write_text("owned replacement")
        return fd
    monkeypatch.setattr(dm, "_open_root", replace_after_open)
    monkeypatch.setattr(dm.os, "scandir", lambda *_args: pytest.fail("replacement was traversed"))
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    result = scope.observe_once(selection)
    assert result["state"] == "root_changed" and result["observation"] is None


@POSIX
def test_final_address_rewalk_rejects_change_after_scanner_completion(tmp_path, monkeypatch):
    root = project(tmp_path)
    selection = scope.select_root(str(root))
    original_scan = dm.scan_storage
    def scan_then_replace(*args, **kwargs):
        value = original_scan(*args, **kwargs)
        root.rename(tmp_path / "retired-owned-project")
        root.mkdir()
        return value
    monkeypatch.setattr(dm, "scan_storage", scan_then_replace)
    result = scope.observe_once(selection)
    assert result["state"] == "root_changed" and result["observation"] is None


@POSIX
def test_limits_are_forced_and_no_previous_or_clock_can_be_injected(tmp_path, monkeypatch):
    root = project(tmp_path)
    seen = {}
    original = dm.scan_storage
    def capture(roots, **kwargs):
        seen.update(roots=roots, **kwargs)
        return original(roots, **kwargs)
    monkeypatch.setattr(dm, "scan_storage", capture)
    result = scope.observe_once(scope.select_root(str(root)))
    assert result["state"] == "observed"
    limits = seen["limits"]
    assert (limits.max_entries, limits.max_directory_entries, limits.max_depth, limits.max_seconds) == (2000, 500, 8, 5)
    assert limits.hash_files is False and limits.cross_filesystems is False
    assert seen["previous"] is None and "started_at" not in seen
    assert seen["roots"] == [str(root)]
    assert callable(seen["root_guard"])


@POSIX
def test_directory_and_depth_limits_return_partial_not_false_empty(tmp_path):
    root = project(tmp_path)
    wide = root / "wide"
    wide.mkdir()
    for number in range(501):
        (wide / str(number)).touch()
    deep = root
    for _ in range(10):
        deep = deep / "nested"
        deep.mkdir()
    result = scope.observe_once(scope.select_root(str(root)))
    assert result["state"] == "partial"
    reasons = {item["reason"] for item in result["observation"]["scan"]["exclusions"]}
    assert {"directory_entry_limit", "depth_limit"} <= reasons
    assert result["observation"]["scan"]["coverage"]["complete_within_policy"] is False
    assert any(entry["relative_path"] == "notes.txt" for entry in result["observation"]["entries"])


@POSIX
def test_copy_deepcopy_pickle_and_wrong_process_cannot_reuse_selection(tmp_path, monkeypatch):
    selection = scope.select_root(str(project(tmp_path)))
    held = selection._fd
    for operation in (copy.copy, copy.deepcopy, pickle.dumps, json.dumps):
        with pytest.raises(TypeError):
            operation(selection)
    real_pid = os.getpid()
    class ForbiddenLock:
        def __enter__(self):
            pytest.fail("changed process touched inherited lock")
        def __exit__(self, *_args):
            pass
    lock = selection._lock
    selection._lock = ForbiddenLock()
    with monkeypatch.context() as context:
        context.setattr(scope.os, "getpid", lambda: real_pid + 1)
        for action in (selection.revoke, selection.close, lambda: selection.state,
                       lambda: scope.observe_once(selection)):
            with pytest.raises(scope.SelectionError, match="another process"):
                action()
    selection._lock = lock
    assert os.fstat(held)
    selection.close()
    assert_closed(held)


@POSIX
def test_concurrent_second_attempt_rejects_and_revoke_does_not_close_active_fd(tmp_path):
    selection = scope.select_root(str(project(tmp_path)))
    held = selection._fd
    entered, release = threading.Event(), threading.Event()
    def progress(_value):
        entered.set()
        assert release.wait(3)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(scope.observe_once, selection, progress=progress)
        assert entered.wait(3)
        with pytest.raises(scope.SelectionError):
            scope.observe_once(selection)
        selection.revoke()
        assert os.fstat(held)
        release.set()
        result = future.result(timeout=3)
    assert result["state"] == "revoked" and result["observation"] is None
    assert_closed(held)


@pytest.mark.parametrize("value", [None, {}, "selection", 7, object()])
def test_descriptions_are_not_usable_selections(value):
    with pytest.raises(scope.SelectionError):
        scope.observe_once(value)


@POSIX
@pytest.mark.parametrize("failure", [PermissionError, FileNotFoundError])
def test_descendant_errors_preserve_explicit_partial_inventory(tmp_path, monkeypatch, failure):
    root = project(tmp_path)
    (root / "lost.txt").write_text("owned metadata fixture")
    original = os.stat
    def observe(path, *args, **kwargs):
        if path == "lost.txt":
            raise failure("controlled owned fixture failure")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(dm.os, "stat", observe)
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    result = scope.observe_once(scope.select_root(str(root)))
    assert result["state"] == "partial"
    missing = next(entry for entry in result["observation"]["entries"] if entry["relative_path"] == "lost.txt")
    assert missing["status"] == ("unreadable" if failure is PermissionError else "disappeared")
    assert result["observation"]["scan"]["coverage"]["complete_within_policy"] is False


@POSIX
def test_time_budget_after_progress_retains_only_partial_observations(tmp_path, monkeypatch):
    root = project(tmp_path)
    clock = [0.0]
    monkeypatch.setattr(dm.time, "monotonic", lambda: clock[0])
    def progress(_value):
        clock[0] = 6.0
    result = scope.observe_once(scope.select_root(str(root)), progress=progress)
    assert result["state"] == "partial"
    assert result["observation"]["scan"]["coverage"]["stop_reason"] == "time_limit"
    assert result["observation"]["scan"]["coverage"]["complete_within_policy"] is False


@POSIX
def test_entry_budget_is_fixed_and_explicit(tmp_path):
    root = project(tmp_path)
    for directory in range(4):
        folder = root / f"batch-{directory}"
        folder.mkdir()
        for number in range(500):
            (folder / str(number)).touch()
    result = scope.observe_once(scope.select_root(str(root)))
    assert result["state"] == "partial"
    assert len(result["observation"]["entries"]) == 2000
    assert result["observation"]["scan"]["coverage"]["stop_reason"] == "entry_limit"


@POSIX
def test_filesystem_boundary_does_not_descend(tmp_path, monkeypatch):
    root = project(tmp_path)
    other = root / "other-filesystem"
    other.mkdir()
    (other / "not-enumerated.txt").write_text("owned sentinel")
    original = os.stat
    def observe(path, *args, **kwargs):
        value = original(path, *args, **kwargs)
        if path == "other-filesystem":
            class Metadata:
                def __getattr__(self, name):
                    return value.st_dev + 1 if name == "st_dev" else getattr(value, name)
            return Metadata()
        return value
    monkeypatch.setattr(dm.os, "stat", observe)
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    result = scope.observe_once(scope.select_root(str(root)))
    assert result["state"] == "partial"
    assert "filesystem_boundary" in {item["reason"] for item in result["observation"]["scan"]["exclusions"]}
    assert not any("not-enumerated" in entry["relative_path"] for entry in result["observation"]["entries"])


@POSIX
def test_scope_change_takes_priority_over_observed_cancellation(tmp_path):
    root = project(tmp_path)
    selection = scope.select_root(str(root))
    changed = False
    def progress(_value):
        nonlocal changed
        if not changed:
            root.rename(tmp_path / "moved-owned-project")
            root.mkdir()
            changed = True
    result = scope.observe_once(selection, progress=progress, cancel=lambda: changed)
    assert result["state"] == "root_changed" and result["observation"] is None
    assert selection._cancelled is True and selection._changed is True


@POSIX
def test_callbacks_run_outside_lock_and_may_admit_revoke_from_another_thread(tmp_path):
    root = project(tmp_path)
    selection = scope.select_root(str(root))
    observed = []
    def callback(_value=None):
        with ThreadPoolExecutor(max_workers=1) as pool:
            def inspect_lock():
                acquired = selection._lock.acquire(timeout=1)
                if acquired:
                    selection._lock.release()
                return acquired
            observed.append(pool.submit(inspect_lock).result(timeout=2))
        return False
    result = scope.observe_once(selection, cancel=callback, progress=callback)
    assert result["state"] == "observed" and observed and all(observed)


@POSIX
def test_already_admitted_progress_finishes_after_revoke_but_no_later_callback_starts(tmp_path):
    selection = scope.select_root(str(project(tmp_path)))
    entered, release = threading.Event(), threading.Event()
    starts, finishes = [], []
    def progress(value):
        starts.append(value)
        entered.set()
        assert release.wait(3)
        finishes.append(value)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(scope.observe_once, selection, progress=progress)
        try:
            assert entered.wait(3)
            selection.revoke()
        finally:
            release.set()
        result = future.result(timeout=3)
    assert result["state"] == "revoked" and result["observation"] is None
    assert len(starts) == len(finishes) == 1


@POSIX
def test_inflight_scanner_completion_after_revoke_is_discarded(tmp_path, monkeypatch):
    selection = scope.select_root(str(project(tmp_path)))
    entered, release = threading.Event(), threading.Event()
    original = dm.scan_storage
    def controlled_call(*args, **kwargs):
        value = original(*args, **kwargs)
        entered.set()
        assert release.wait(3)
        return value
    monkeypatch.setattr(dm, "scan_storage", controlled_call)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(scope.observe_once, selection)
        try:
            assert entered.wait(3)
            selection.revoke()
        finally:
            release.set()
        result = future.result(timeout=3)
    assert result["state"] == "revoked" and result["observation"] is None


@POSIX
def test_result_admitted_before_later_revoke_has_no_continuing_authority(tmp_path, monkeypatch):
    selection = scope.select_root(str(project(tmp_path)))
    original = scope._result
    def revoke_after_admission(outcome, inventory=None):
        if outcome == "observed":
            selection.revoke()
        return original(outcome, inventory)
    monkeypatch.setattr(scope, "_result", revoke_after_admission)
    result = scope.observe_once(selection)
    assert result["state"] == "observed" and result["observation"] is not None
    assert selection.state == "revoked"
    assert_no_authority(result)
    with pytest.raises(scope.SelectionError):
        scope.observe_once(selection)


@POSIX
def test_capability_loss_after_selection_abstains_without_reopening(tmp_path, monkeypatch):
    selection = scope.select_root(str(project(tmp_path)))
    held = selection._fd
    monkeypatch.setattr(dm, "traversal_supported", lambda: False)
    monkeypatch.setattr(dm, "_open_root", lambda *_args: pytest.fail("weak fallback open"))
    result = scope.observe_once(selection)
    assert result["state"] == "unsupported" and result["observation"] is None
    assert_closed(held)


@POSIX
def test_no_network_subprocess_mutation_or_executor_import_during_observation(tmp_path, monkeypatch):
    import builtins
    import socket
    import subprocess
    root = project(tmp_path)
    selection = scope.select_root(str(root))
    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden during owned metadata observation")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(os, "unlink", forbidden)
    monkeypatch.setattr(os, "remove", forbidden)
    monkeypatch.setattr(os, "rename", forbidden)
    monkeypatch.setattr(os, "replace", forbidden)
    original_import = builtins.__import__
    blocked = {"app", "guided", "op_store", "fs_ops", "tasks", "safety"}
    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"backend." + item for item in blocked} or (name == "backend" and blocked.intersection(fromlist)):
            raise AssertionError("executor/provider import during observation")
        return original_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, "__import__", safe_import)
    result = scope.observe_once(selection)
    assert result["state"] == "observed"


@POSIX
def test_base_exception_retires_descriptor_without_admitting_result(tmp_path, monkeypatch):
    selection = scope.select_root(str(project(tmp_path)))
    held = selection._fd
    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt("owned test interruption")
    monkeypatch.setattr(dm, "scan_storage", interrupt)
    with pytest.raises(KeyboardInterrupt):
        scope.observe_once(selection)
    assert selection.state == "spent"
    assert_closed(held)


@POSIX
def test_reentrant_revocation_during_scope_comparison_cannot_admit_guard(tmp_path, monkeypatch):
    selection = scope.select_root(str(project(tmp_path)))
    original_same = scope._same_directory
    original_scan = dm.scan_storage
    guard_results = []
    def compare_and_revoke(*args):
        selection.revoke()
        return original_same(*args)
    def capture_guard(roots, **kwargs):
        guard = kwargs["root_guard"]
        def capture(*args):
            result = guard(*args)
            guard_results.append(result)
            return result
        return original_scan(roots, **{**kwargs, "root_guard": capture})
    monkeypatch.setattr(scope, "_same_directory", compare_and_revoke)
    monkeypatch.setattr(dm, "scan_storage", capture_guard)
    result = scope.observe_once(selection)
    assert result["state"] == "revoked" and result["observation"] is None
    assert guard_results == [False]


def test_session_module_imports_only_the_scanner_and_standard_library():
    import ast
    from pathlib import Path
    source = ast.parse(Path(scope.__file__).read_text())
    for node in ast.walk(source):
        if isinstance(node, ast.Import):
            assert all(alias.name in {"os", "posixpath", "stat", "threading"} for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module in {"__future__", "contextlib", "backend"}
            if node.module == "backend":
                assert [alias.name for alias in node.names] == ["disk_model"]


@POSIX
def test_native_backslash_spelling_is_preserved_as_observation_data(tmp_path):
    root = project(tmp_path)
    (root / "native\\name.txt").write_text("owned native spelling")
    result = scope.observe_once(scope.select_root(str(root)))
    assert result["state"] == "observed"
    assert any(entry["relative_path"] == "native\\name.txt" for entry in result["observation"]["entries"])
    dm.validate_inventory(result["observation"])
    assert_no_authority(result)


@POSIX
def test_invalid_canonical_producer_metadata_is_not_admitted(tmp_path, monkeypatch):
    root = project(tmp_path)
    original = dm.scan_storage
    def corrupt(*args, **kwargs):
        value = original(*args, **kwargs)
        next(entry for entry in value["entries"] if entry["kind"] == "file")["logical_bytes"] = -1
        return value
    monkeypatch.setattr(dm, "scan_storage", corrupt)
    result = scope.observe_once(scope.select_root(str(root)))
    assert result["state"] == "failed" and result["observation"] is None
    assert_no_authority(result)
