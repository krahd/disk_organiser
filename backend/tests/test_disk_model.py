"""All storage fixtures are synthetic temporary trees; no real user folders."""
import hashlib
import json
import os

import pytest

from backend import disk_model as dm
from backend.disk_model_analysis import analyse_inventory
from backend.disk_model_cli import load_export, main
from backend.disk_model_fixture import synthetic_model

POSIX = pytest.mark.skipif(not dm.traversal_supported(), reason="Descriptor-relative scanner intentionally abstains")
FIXED_TIME = "2026-10-06T12:00:00+00:00"


def scan(root, **kwargs):
    return dm.scan_storage([str(root)], started_at=FIXED_TIME, **kwargs)


def file_entry(model, name):
    return next(e for e in model["entries"] if e["relative_path"] == name)


def kinds(model):
    return {e["kind"] for e in model["relationships"]}


@POSIX
def test_metadata_first_does_not_read_file_contents(tmp_path, monkeypatch):
    (tmp_path / "private.txt").write_text("synthetic only")
    real_open = os.open

    def only_directories(path, flags, *args, **kwargs):
        assert flags & os.O_DIRECTORY
        assert not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(dm.os, "open", only_directories)
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    model = scan(tmp_path)
    assert model["scan"]["status"] == "complete"
    assert model["scan"]["hash_policy"] == "metadata_only"
    assert model["scan"]["coverage"]["hashed_bytes"] == 0
    assert all(e["hash"]["status"] == "disabled" for e in model["entries"])
    assert "exact_content_match" not in kinds(model)
    assert model["aggregates"]["recoverable_bytes"] is None


@POSIX
def test_hashes_exact_distinct_objects_not_deletion_permission(tmp_path):
    for name in ("a.txt", "b.txt"):
        (tmp_path / name).write_bytes(b"same synthetic bytes")
    model = scan(tmp_path, limits=dm.ScanLimits(hash_files=True))
    relationship = next(e for e in model["relationships"] if e["kind"] == "exact_content_match")
    assert relationship["confidence"] == "observed"
    assert file_entry(model, "a.txt")["hash"]["value"] == hashlib.sha256(b"same synthetic bytes").hexdigest()
    assert "safe to delete" in " ".join(relationship["uncertainties"])
    assert all(not p["executable"] for p in model["plan_alternatives"])
    assert model["aggregates"]["recoverable_bytes"] is None


@POSIX
def test_hardlinks_count_paths_and_objects_separately(tmp_path):
    source = tmp_path / "first.txt"
    source.write_bytes(b"hello")
    os.link(source, tmp_path / "alias.txt")
    model = scan(tmp_path, limits=dm.ScanLimits(hash_files=True))
    assert kinds(model) == {"hard_link_paths"}
    assert model["aggregates"]["logical_bytes_by_path"] == 10
    assert model["aggregates"]["logical_bytes_by_observed_object"] == 5
    assert model["aggregates"]["hard_link_alias_paths"] == 1


@POSIX
def test_equal_metadata_without_hash_is_not_exact_match(tmp_path):
    for name in ("a.txt", "b.txt"):
        (tmp_path / name).write_bytes(b"same size")
    model = scan(tmp_path)
    assert not model["relationships"]


@POSIX
def test_version_names_hypothesis_not_lineage(tmp_path):
    for name in ("design_v1.blend", "design_v2.blend", "different_v3.blend"):
        (tmp_path / name).write_text(name)
    model = scan(tmp_path)
    relation = next(r for r in model["relationships"] if r["kind"] == "version_like_names")
    assert relation["confidence"] == "hypothesis"
    assert len(relation["member_ids"]) == 2
    assert "lineage" in " ".join(relation["uncertainties"])


@POSIX
def test_directory_roles_abstain_and_aggregate_nested_paths(tmp_path):
    archive = tmp_path / "Archive"
    archive.mkdir()
    (archive / "package.json").write_bytes(b"{}")
    nested = archive / "nested"
    nested.mkdir()
    (nested / "notes.txt").write_bytes(b"12345")
    model = scan(tmp_path)
    root = next(d for d in model["directories"] if d["entry_id"] == file_entry(model, ".")["id"])
    archived = next(d for d in model["directories"] if d["entry_id"] == file_entry(model, "Archive")["id"])
    assert root["logical_bytes"] == 7
    assert archived["logical_bytes"] == 7
    assert root["confidence"] == "unknown"
    assert {h["role"] for h in archived["role_hypotheses"]} == {"project", "archive"}
    assert any(f["counter_evidence"] for f in model["findings"])


@POSIX
def test_links_special_files_and_cloud_markers_not_read(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("synthetic")
    root = tmp_path / "selected"
    root.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    os.mkfifo(root / "pipe")
    (root / "cloud.icloud").write_text("synthetic placeholder")
    model = scan(root, limits=dm.ScanLimits(hash_files=True))
    assert len(model["entries"]) == 4
    assert model["scan"]["status"] == "partial"
    assert all(e["status"] == "unsupported" for e in model["entries"] if e["relative_path"] != ".")
    assert model["scan"]["coverage"]["hashed_bytes"] == 0


@POSIX
def test_symlink_root_and_symlink_ancestor_rejected(tmp_path):
    selected = tmp_path / "real"
    selected.mkdir()
    child = selected / "sub"
    child.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(selected, target_is_directory=True)
    for root in (alias, alias / "sub"):
        model = scan(root)
        assert model["scan"]["status"] == "partial"
        assert model["scan"]["errors"]
        assert len(model["entries"]) == 1


@POSIX
def test_budget_limits_never_advertise_hash_for_unread_data(tmp_path):
    (tmp_path / "a").write_bytes(b"12345")
    (tmp_path / "b").write_bytes(b"12345")
    (tmp_path / "large").write_bytes(b"123456789")
    limits = dm.ScanLimits(hash_files=True, max_hash_file_bytes=8, max_hash_total_bytes=5)
    model = scan(tmp_path, limits=limits)
    assert file_entry(model, "a")["hash"]["status"] == "verified"
    assert file_entry(model, "b")["hash"]["status"] == "hash_budget_limit"
    assert file_entry(model, "large")["hash"]["status"] == "file_byte_limit"
    assert model["scan"]["coverage"]["hashed_bytes"] == 5
    assert "exact_content_match" not in kinds(model)


@POSIX
def test_empty_files_have_real_bounded_digest(tmp_path):
    (tmp_path / "empty-a").touch()
    (tmp_path / "empty-b").touch()
    model = scan(tmp_path, limits=dm.ScanLimits(hash_files=True, max_hash_files=1))
    assert file_entry(model, "empty-a")["hash"]["value"] == hashlib.sha256(b"").hexdigest()
    assert file_entry(model, "empty-b")["hash"]["status"] == "hash_budget_limit"


@POSIX
def test_directory_entry_limit_abstains_instead_of_arbitrary_subset(tmp_path):
    for name in ("c", "b", "a"):
        (tmp_path / name).touch()
    model = scan(tmp_path, limits=dm.ScanLimits(max_directory_entries=2))
    assert len(model["entries"]) == 1
    assert model["scan"]["exclusions"][0]["reason"] == "directory_entry_limit"
    assert model["aggregates"]["partial"]


@POSIX
def test_total_entry_depth_and_exclusion_limits(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "nested").write_text("synthetic")
    (tmp_path / "b").touch()
    model = scan(tmp_path, limits=dm.ScanLimits(max_entries=2))
    assert len(model["entries"]) == 2
    assert model["scan"]["coverage"]["stop_reason"] == "entry_limit"
    model = scan(tmp_path, limits=dm.ScanLimits(max_depth=1))
    assert "depth_limit" in {e["reason"] for e in model["scan"]["exclusions"]}
    model = scan(tmp_path, limits=dm.ScanLimits(exclude_names=("a",)))
    assert file_entry(model, "a")["status"] == "excluded"
    assert not any(e["relative_path"].startswith("a/") for e in model["entries"])
    assert model["scan"]["status"] == "partial"


@POSIX
def test_cancel_returns_partial_evidence_and_final_progress(tmp_path):
    for number in range(8):
        (tmp_path / str(number)).touch()
    progress = []
    model = scan(tmp_path, cancel=lambda: bool(progress), progress=progress.append)
    assert model["scan"]["status"] == "cancelled"
    assert progress[-1]["status"] == "cancelled"
    assert len(model["entries"]) < 9


@POSIX
def test_time_budget_is_explicit_partial(tmp_path, monkeypatch):
    ticks = iter((0, 100))
    monkeypatch.setattr(dm.time, "monotonic", lambda: next(ticks))
    model = scan(tmp_path, limits=dm.ScanLimits(max_seconds=1))
    assert model["scan"]["coverage"]["stop_reason"] == "time_limit"
    assert model["scan"]["roots"][0]["status"] == "unvisited"


@POSIX
def test_disappeared_entry_recorded_not_silently_omitted(tmp_path, monkeypatch):
    (tmp_path / "gone").touch()
    real_stat = os.stat

    def disappears(path, *args, **kwargs):
        if path == "gone":
            raise FileNotFoundError(2, "synthetic disappeared")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(dm.os, "stat", disappears)
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    model = scan(tmp_path)
    assert file_entry(model, "gone")["status"] == "disappeared"
    assert model["scan"]["status"] == "partial"


@POSIX
def test_unreadable_directory_recorded(tmp_path, monkeypatch):
    (tmp_path / "blocked").mkdir()
    real_open = os.open

    def blocked(path, *args, **kwargs):
        if path == "blocked":
            raise PermissionError(13, "synthetic permission denial")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(dm.os, "open", blocked)
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    model = scan(tmp_path)
    assert file_entry(model, "blocked")["status"] == "unreadable"
    assert model["scan"]["errors"][0]["kind"] == "PermissionError"


@POSIX
def test_hash_change_during_read_is_stale_not_duplicate(tmp_path, monkeypatch):
    source = tmp_path / "a"
    source.write_bytes(b"1234")
    (tmp_path / "b").write_bytes(b"1234")
    real_read = os.read
    changed = False

    def mutation(fd, size):
        nonlocal changed
        chunk = real_read(fd, size)
        if not changed:
            changed = True
            source.write_bytes(b"56789")
        return chunk

    monkeypatch.setattr(dm.os, "read", mutation)
    model = scan(tmp_path, limits=dm.ScanLimits(hash_files=True))
    assert file_entry(model, "a")["status"] == "stale"
    assert file_entry(model, "a")["hash"]["status"] == "stale"
    assert model["scan"]["status"] == "partial"
    assert "exact_content_match" not in kinds(model)


@POSIX
def test_incremental_deltas_never_trust_previous_hashes(tmp_path):
    (tmp_path / "a").write_text("synthetic")
    before = scan(tmp_path)
    before["entries"][-1]["hash"] = {"status": "verified", "algorithm": "sha256", "value": "0" * 64}
    (tmp_path / "b").write_text("new")
    after = scan(tmp_path, previous=before)
    assert file_entry(before, "a")["id"] == file_entry(after, "a")["id"]
    assert file_entry(after, "b")["id"] in after["changes"]["added"]
    assert file_entry(after, "a")["id"] in after["changes"]["unchanged_metadata"]
    assert after["changes"]["hashes_reused"] == 0
    assert file_entry(after, "a")["hash"]["status"] == "disabled"
    (tmp_path / "a").unlink()
    removed = scan(tmp_path, previous=after)
    assert file_entry(after, "a")["id"] in removed["changes"]["no_longer_observed"]
    partial = scan(tmp_path, previous=after, cancel=lambda: True)
    assert not partial["changes"]["no_longer_observed"]
    assert partial["changes"]["unverified_absent"]


@POSIX
def test_reproducible_with_fixed_scan_timestamp(tmp_path):
    (tmp_path / "x.txt").write_text("synthetic")
    one = dm.export_json(scan(tmp_path))
    two = dm.export_json(scan(tmp_path))
    assert one == two
    assert "NaN" not in one


def test_platform_abstention_without_weak_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(dm, "traversal_supported", lambda: False)
    model = scan(tmp_path)
    assert model["scan"]["status"] == "partial"
    assert model["entries"][0]["status"] == "unsupported"
    assert model["aggregates"]["recoverable_bytes"] is None


@pytest.mark.parametrize("kwargs", [{"max_entries": 0}, {"max_entries": True}, {"max_depth": 1000},
                                    {"max_seconds": float("nan")}, {"hash_files": 1},
                                    {"exclude_names": ("../x",)}, {"max_hash_files": 0}])
def test_invalid_limits_rejected(kwargs):
    with pytest.raises(ValueError):
        dm.ScanLimits(**kwargs)


def test_overlapping_roots_rejected_before_traversal(tmp_path):
    with pytest.raises(ValueError, match="Overlapping"):
        dm.scan_storage([str(tmp_path), str(tmp_path / "nested")])


def test_unknown_allocation_stays_unknown():
    model = synthetic_model()
    assert model["aggregates"]["allocation_unknown_objects"] == 1
    for entry in model["entries"]:
        entry["allocated_bytes"] = None
    analysed = analyse_inventory(model)
    assert analysed["aggregates"]["known_allocated_bytes_by_observed_object"] is None
    assert analysed["aggregates"]["physical_bytes"] is None


def test_evidence_plan_links_resolve_and_no_mutation_step_exists():
    model = synthetic_model()
    entries = {e["id"] for e in model["entries"]}
    facts = {e["id"] for e in model["evidence"]}
    findings = {e["id"] for e in model["findings"]}
    assert {f["confidence"] for f in model["findings"]} == {"observed", "hypothesis", "unknown"}
    for found in model["findings"] + model["relationships"]:
        assert set(found["member_ids"]) <= entries
        assert set(found["evidence_ids"]) <= facts
    for plan in model["plan_alternatives"]:
        assert plan["executable"] is False
        assert set(plan["finding_ids"]) <= findings
        for alternative in plan["alternatives"]:
            seen = set()
            for step in alternative["steps"]:
                assert step["type"] in {"keep_unchanged", "inspect_evidence", "ask_about_intent"}
                assert set(step["depends_on"]) <= seen
                assert set(step["member_ids"]) <= entries
                assert set(step["evidence_ids"]) <= facts
                seen.add(step["id"])
            assert alternative["unchanged_member_ids"] == plan["scope_member_ids"]
            assert alternative["expected_consequences"]["filesystem_changes"] == 0


def test_query_pagination_is_stable_and_does_not_change_totals():
    model = synthetic_model()
    totals = dict(model["aggregates"])
    result = dm.query_entries(model, kind="file", limit=2)
    assert len(result["entries"]) == 2
    assert result["next_offset"] == 2
    more = dm.query_entries(model, kind="file", offset=2, limit=2)
    assert not {e["id"] for e in more["entries"]} & {e["id"] for e in result["entries"]}
    assert model["aggregates"] == totals
    with pytest.raises(ValueError):
        dm.query_entries(model, limit=1001)


def test_fixture_cli_export_and_query(tmp_path, capsys):
    assert main(["fixture"]) == 0
    content = capsys.readouterr().out
    model = json.loads(content)
    assert model["synthetic"] is True
    path = tmp_path / "fixture.json"
    path.write_text(content)
    assert load_export(str(path)) == model
    assert main(["query", str(path), "--path-contains", "design", "--limit", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["total_matching"] == 2


@POSIX
def test_scan_cli_partial_exit_preserves_json(tmp_path, capsys):
    (tmp_path / "a").touch()
    assert main(["scan", str(tmp_path), "--max-entries", "1", "--progress"]) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out)["scan"]["status"] == "partial"
    assert json.loads(captured.err.strip())["status"] == "partial"


def test_cli_rejects_bad_export(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text('{"schema_version":"wrong"}')
    assert main(["query", str(path)]) == 1
    assert "input error" in capsys.readouterr().err


def test_fixture_is_deterministic_and_schema_uses_explicit_limits():
    assert dm.export_json(synthetic_model()) == dm.export_json(synthetic_model())
    assert synthetic_model()["scan"]["limits"] == dm.ScanLimits(hash_files=True).to_dict()


@POSIX
def test_hash_race_to_symlink_never_reads_outside_selected_root(tmp_path, monkeypatch):
    root = tmp_path / "selected"
    root.mkdir()
    source = root / "a"
    source.write_text("synthetic in root")
    outside = tmp_path / "outside.txt"
    outside.write_text("synthetic outside root")
    real_open = os.open

    def replace_before_open(path, flags, *args, **kwargs):
        if path == "a":
            source.unlink()
            source.symlink_to(outside)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(dm.os, "open", replace_before_open)
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    model = scan(root, limits=dm.ScanLimits(hash_files=True))
    assert model["scan"]["coverage"]["hashed_bytes"] == 0
    assert file_entry(model, "a")["hash"]["status"] != "verified"
    assert model["scan"]["status"] == "partial"


@POSIX
def test_changed_ancestor_invalidates_descendant_evidence(tmp_path):
    root = tmp_path / "selected"
    root.mkdir()
    (root / "a").write_text("synthetic")
    changed = False

    def relocate(_event):
        nonlocal changed
        if not changed:
            changed = True
            root.rename(tmp_path / "relocated")

    model = scan(root, limits=dm.ScanLimits(hash_files=True), progress=relocate)
    assert model["scan"]["status"] == "partial"
    assert file_entry(model, "a")["status"] == "stale"
    assert file_entry(model, "a")["hash"]["value"] is None
    assert model["aggregates"]["observed_regular_files"] == 0


@POSIX
def test_exported_previous_policy_compares_equal(tmp_path):
    (tmp_path / "a").write_text("synthetic")
    before = json.loads(dm.export_json(scan(tmp_path)))
    after = scan(tmp_path, previous=before)
    assert after["changes"]["comparable"] is True


def test_old_mtime_is_not_dormancy_or_disposal_claim():
    model = synthetic_model()
    found = next(f for f in model["findings"] if f["kind"] == "older_modification_times")
    assert found["confidence"] == "observed"
    assert "does not show last use" in " ".join(found["uncertainties"])


@pytest.mark.parametrize("field,value", [("relative_path", "../escape"), ("logical_bytes", -1),
                                         ("status", "safe_to_delete"), ("root_id", "unknown")])
def test_import_rejects_invalid_metadata(field, value):
    model = synthetic_model()
    model["entries"][0][field] = value
    with pytest.raises(ValueError):
        dm.validate_inventory(model)


def test_committed_fixture_matches_generator():
    from pathlib import Path
    path = Path(__file__).parent / "fixtures" / "disk-model-v1.json"
    assert path.read_text() == dm.export_json(synthetic_model())


@POSIX
def test_replaced_root_is_not_comparable_refresh(tmp_path):
    root = tmp_path / "selected"
    root.mkdir()
    (root / "a").write_text("synthetic")
    before = scan(root)
    root.rename(tmp_path / "prior-root")
    root.mkdir()
    after = scan(root, previous=before)
    assert after["changes"]["comparable"] is False
    assert not after["changes"]["no_longer_observed"]
    assert after["changes"]["unverified_absent"]


def test_name_exclusions_reject_string_instead_of_sequence():
    with pytest.raises(ValueError):
        dm.ScanLimits(exclude_names="abc")


@POSIX
def test_renamed_ancestor_above_root_invalidates_entries(tmp_path):
    parent = tmp_path / "parent"
    root = parent / "selected"
    root.mkdir(parents=True)
    (root / "a").write_text("synthetic")
    changed = False

    def relocate(_event):
        nonlocal changed
        if not changed:
            changed = True
            parent.rename(tmp_path / "renamed-parent")

    model = scan(root, limits=dm.ScanLimits(hash_files=True), progress=relocate)
    assert model["scan"]["status"] == "partial"
    assert file_entry(model, "a")["status"] == "stale"
    assert file_entry(model, "a")["hash"]["value"] is None
    assert not root.exists()


@POSIX
def test_failed_hash_attempts_consume_file_read_budget(tmp_path, monkeypatch):
    for name in ("a", "b", "c"):
        (tmp_path / name).write_bytes(b"1234")
    real_read = os.read

    def rewrite(fd, size):
        chunk = real_read(fd, size)
        for name in ("a", "b", "c"):
            (tmp_path / name).write_bytes(b"56789")
        return chunk

    monkeypatch.setattr(dm.os, "read", rewrite)
    model = scan(tmp_path, limits=dm.ScanLimits(hash_files=True, max_hash_files=1))
    assert model["scan"]["coverage"]["hash_attempts"] == 1
    assert model["scan"]["coverage"]["hashed_files"] == 0
    assert model["scan"]["coverage"]["hashed_bytes"] == 4
    assert file_entry(model, "b")["hash"]["status"] == "hash_budget_limit"
    assert file_entry(model, "c")["hash"]["status"] == "hash_budget_limit"


@POSIX
def test_stale_hardlink_invalidates_previously_verified_alias(tmp_path, monkeypatch):
    source = tmp_path / "a"
    source.write_bytes(b"1234")
    os.link(source, tmp_path / "b")
    (tmp_path / "c").write_bytes(b"1234")
    real_read = os.read
    calls = 0

    def rewrite_second(fd, size):
        nonlocal calls
        chunk = real_read(fd, size)
        calls += 1
        if calls == 2:
            source.write_bytes(b"56789")
        return chunk

    monkeypatch.setattr(dm.os, "read", rewrite_second)
    model = scan(tmp_path, limits=dm.ScanLimits(hash_files=True))
    assert file_entry(model, "a")["status"] == "stale"
    assert file_entry(model, "a")["hash"]["value"] is None
    assert file_entry(model, "b")["status"] == "stale"
    assert "exact_content_match" not in kinds(model)


def test_missing_object_identity_cannot_prove_distinct_copies():
    model = synthetic_model()
    for entry in model["entries"]:
        if entry["kind"] == "file":
            entry["object_id"] = None
    model.update(analyse_inventory(model))
    assert "exact_content_match" not in kinds(model)
    for field in ("distinct_observed_file_objects", "logical_bytes_by_observed_object",
                  "hard_link_alias_paths", "known_allocated_bytes_by_observed_object", "allocation_unknown_objects"):
        assert model["aggregates"][field] is None
    assert model["aggregates"]["object_identity_unknown_paths"] == 9
    uncertain = next(r for r in model["relationships"] if r["kind"] == "content_match_identity_unknown")
    assert "hard-link aliases" in " ".join(uncertain["uncertainties"])


@POSIX
def test_truncated_directory_does_not_look_empty(tmp_path):
    directory = tmp_path / "nonempty"
    directory.mkdir()
    (directory / "a").write_text("synthetic")
    model = scan(tmp_path, limits=dm.ScanLimits(max_depth=1))
    child = next(d for d in model["directories"] if d["entry_id"] == file_entry(model, "nonempty")["id"])
    root = next(d for d in model["directories"] if d["entry_id"] == file_entry(model, ".")["id"])
    assert child["logical_bytes"] == 0
    assert child["coverage"] == {"complete": False, "reasons": ["depth_limit"]}
    assert root["coverage"]["complete"] is False
    assert "descendant_coverage_incomplete" in root["coverage"]["reasons"]


@pytest.mark.parametrize("malformation", ["limit", "fingerprint", "executable", "traversal", "digest", "reference"])
def test_full_contract_import_rejects_malformed_model(tmp_path, malformation):
    model = synthetic_model()
    if malformation == "limit":
        model["scan"]["limits"]["max_hash_files"] = 10**10
    elif malformation == "fingerprint":
        model["entries"][0]["fingerprint"] = {"arbitrary": True}
    elif malformation == "executable":
        model["plan_alternatives"][0]["executable"] = True
    elif malformation == "traversal":
        model["entries"][0]["relative_path"] = "../escape"
    elif malformation == "digest":
        model["entries"][0]["hash"] = {"status": "verified", "algorithm": None, "value": None}
    else:
        model["findings"][0]["evidence_ids"] = ["missing"]
    path = tmp_path / "malformed.json"
    path.write_text(json.dumps(model))
    with pytest.raises(ValueError):
        load_export(str(path))


def test_runtime_schema_and_published_schema_match_and_validate_fixture():
    from pathlib import Path
    from backend.disk_model_schema import SCHEMA, validate_contract
    schema_path = Path(__file__).parents[2] / "docs" / "disk-model-v1.schema.json"
    assert json.loads(schema_path.read_text()) == SCHEMA
    validate_contract(synthetic_model())
    dm.validate_inventory(synthetic_model())


@POSIX
def test_runtime_schema_validates_complete_partial_and_cancelled_scans(tmp_path):
    (tmp_path / "a").write_text("synthetic")
    models = [scan(tmp_path), scan(tmp_path, limits=dm.ScanLimits(hash_files=True)),
              scan(tmp_path, limits=dm.ScanLimits(max_entries=1)), scan(tmp_path, cancel=lambda: True)]
    for model in models:
        dm.validate_inventory(model)


def test_optional_scope_guard_interface_is_available():
    import inspect
    assert "root_guard" in inspect.signature(dm.scan_storage).parameters


@POSIX
@pytest.mark.parametrize("answer", [False, None, 1, "yes", {}, []])
def test_root_guard_rejects_before_any_child_access(tmp_path, monkeypatch, answer):
    (tmp_path / "private.txt").write_text("owned fixture only")
    seen = []
    def guard(path, fd):
        seen.append((path, os.fstat(fd).st_ino))
        return answer
    def forbidden(*_args, **_kwargs):
        raise AssertionError("guard rejection must precede child access")
    monkeypatch.setattr(dm.os, "scandir", forbidden)
    # Replacing a supported callable otherwise changes feature introspection.
    monkeypatch.setattr(dm, "traversal_supported", lambda: True)
    result = scan(tmp_path, root_guard=guard)
    assert len(seen) == 1
    assert result["scan"]["status"] == "partial"
    assert result["scan"]["roots"][0]["status"] == "unreadable"
    assert [entry["relative_path"] for entry in result["entries"]] == ["."]


@POSIX
def test_root_guard_success_preserves_exact_default_output(tmp_path):
    (tmp_path / "one.txt").write_text("owned")
    expected = scan(tmp_path)
    assert scan(tmp_path, root_guard=lambda _path, _fd: True) == expected
    assert scan(tmp_path, root_guard=None) == expected


@POSIX
def test_root_guard_exception_closes_borrowed_scanner_descriptor(tmp_path, monkeypatch):
    borrowed = []
    def guard(_path, fd):
        borrowed.append(fd)
        raise RuntimeError("owned test guard interruption")
    with pytest.raises(RuntimeError, match="guard interruption"):
        scan(tmp_path, root_guard=guard)
    with pytest.raises(OSError):
        os.fstat(borrowed[0])


def test_invalid_root_guard_rejects_before_filesystem(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("invalid guard must not open anything")
    monkeypatch.setattr(dm, "_open_root", forbidden)
    for value in (False, 1, "guard", {}):
        with pytest.raises(ValueError, match="root_guard"):
            dm.scan_storage(["/owned-fixture-placeholder"], root_guard=value)
