"""Bounded, local, read-only storage observations. No mutation executor imports.

Directory traversal and optional hashing require descriptor-relative no-follow
operations. Unsupported platforms abstain; importing this module has no I/O.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable

SCHEMA_VERSION = "disk-model/v1"


def stable_id(kind: str, *parts: object) -> str:
    """Stable address ID, not proof of unchanged content or persistent inode identity."""
    payload = json.dumps(parts, ensure_ascii=True, separators=(",", ":"))
    return kind + "_" + hashlib.sha256(payload.encode()).hexdigest()[:24]


@dataclass(frozen=True)
class ScanLimits:
    max_entries: int = 20000
    max_directory_entries: int = 5000
    max_depth: int = 32
    max_seconds: float = 30.0
    hash_files: bool = False
    max_hash_file_bytes: int = 16 * 1024 * 1024
    max_hash_total_bytes: int = 64 * 1024 * 1024
    max_hash_files: int = 1000
    exclude_names: tuple[str, ...] = ()
    cross_filesystems: bool = False

    def __post_init__(self):
        for key, ceiling in (("max_entries", 100000), ("max_directory_entries", 20000),
                             ("max_depth", 64), ("max_hash_file_bytes", 1024**3),
                             ("max_hash_total_bytes", 4 * 1024**3), ("max_hash_files", 10000)):
            value = getattr(self, key)
            if type(value) is not int or value < 1 or value > ceiling:
                raise ValueError(f"{key} must be an integer from 1 to {ceiling}")
        if (type(self.max_seconds) not in (int, float)
                or not 0 < self.max_seconds <= 3600):
            raise ValueError("max_seconds must be positive and at most 3600")
        if type(self.hash_files) is not bool or type(self.cross_filesystems) is not bool:
            raise ValueError("hash_files and cross_filesystems must be booleans")
        if (not isinstance(self.exclude_names, (tuple, list)) or len(self.exclude_names) > 100
                or any(not isinstance(n, str) or not n or n in (".", "..")
                       or "/" in n or "\\" in n for n in self.exclude_names)):
            raise ValueError("exclude_names must contain at most 100 single path components")

    def to_dict(self) -> dict:
        values = asdict(self)
        values["exclude_names"] = list(self.exclude_names)
        return values


def traversal_supported() -> bool:
    return (os.name == "posix" and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
            and os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd
            and os.scandir in os.supports_fd)


def _open_root(path: str) -> int:
    """Reject symlink ancestors too; never resolve a selected root through a link."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(os.path.sep, flags)
    try:
        for component in path.split(os.path.sep):
            if component:
                child = os.open(component, flags, dir_fd=fd)
                os.close(fd)
                fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _root_still_matches(path: str, expected: dict) -> bool:
    """Recheck the selected address, including ancestors which can be renamed."""
    fd = None
    try:
        fd = _open_root(path)
        return _fingerprint(os.fstat(fd)) == expected
    except OSError:
        return False
    finally:
        if fd is not None:
            os.close(fd)


def _fingerprint(st) -> dict:
    return {"device": st.st_dev, "inode": st.st_ino, "size": st.st_size,
            "mtime_ns": st.st_mtime_ns, "ctime_ns": st.st_ctime_ns,
            "mode": st.st_mode, "link_count": st.st_nlink}


def _kind(mode: int) -> str:
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "special"


def _placeholder(st, name: str) -> bool:
    # Known flags only. No claim that other cloud/network files are detected.
    attributes = getattr(st, "st_file_attributes", 0)
    return bool(attributes & (0x1000 | 0x40000 | 0x400000)) or name.endswith(".icloud")


def _entry(root_id: str, relative: str, st=None, status="observed") -> dict:
    kind = _kind(st.st_mode) if st else "unknown"
    return {
        "id": stable_id("entry", root_id, relative), "root_id": root_id,
        "relative_path": relative, "parent_id": None if relative == "." else
        stable_id("entry", root_id, relative.rpartition("/")[0] or "."),
        "kind": kind, "status": status, "logical_bytes": st.st_size if kind == "file" else None,
        "allocated_bytes": (st.st_blocks * 512 if kind == "file" and hasattr(st, "st_blocks") else None),
        "allocation_source": "stat_blocks_512" if kind == "file" and hasattr(st, "st_blocks") else "unknown",
        "object_id": stable_id("object", st.st_dev, st.st_ino) if st and st.st_ino else None,
        "link_count": st.st_nlink if st else None,
        "mtime_ns": st.st_mtime_ns if st else None, "ctime_ns": st.st_ctime_ns if st else None,
        "fingerprint": _fingerprint(st) if st else None,
        "hash": {"status": "disabled", "algorithm": None, "value": None},
        "uncertainties": [],
    }


def scan_storage(roots: list[str], *, limits: ScanLimits | None = None,
                 previous: dict | None = None, cancel: Callable[[], bool] | None = None,
                 progress: Callable[[dict], None] | None = None,
                 started_at: str | None = None) -> dict:
    """Observe explicitly supplied roots; return partial results on bounded interruption.

    No content reads by default. No cache/database writes or remote services.
    ``previous`` only computes deltas; hashes are never trusted/reused from it.
    """
    limits = limits or ScanLimits()
    if not roots or len(roots) > 16 or any(not isinstance(p, str) or not p or "\0" in p for p in roots):
        raise ValueError("Provide 1–16 non-empty root paths")
    paths = sorted({os.path.abspath(p) for p in roots})
    for i, path in enumerate(paths):
        if any(os.path.commonpath([path, other]) == other for other in paths[:i]):
            raise ValueError("Overlapping roots would double-count inventory; select non-overlapping roots")
    if previous is not None:
        validate_inventory(previous)
    scan_time = started_at or datetime.now(timezone.utc).isoformat()
    # Validate timestamp once. Timestamps are observations, never age-based disposal permission.
    stamp = datetime.fromisoformat(scan_time.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("started_at requires a timezone")
    result = {"schema_version": SCHEMA_VERSION, "read_only": True,
              "scan": {"id": None, "started_at": scan_time, "roots": [], "status": "complete",
                       "limits": limits.to_dict(), "coverage": {}, "errors": [], "exclusions": [],
                       "hash_policy": "bounded_sha256" if limits.hash_files else "metadata_only",
                       "uncertainties": ["A scan is not an atomic filesystem snapshot.",
                                         "Cloud placeholders and network mounts are not universally detectable.",
                                         "Allocated bytes are not recoverable physical space.",
                                         "Time/cancellation limits are cooperative; an OS read can block.",
                                         "Metadata/content reads may update filesystem access times.",
                                         "Unhashed or unmatched files are not evidence of uniqueness."]},
              "entries": []}
    entries, scan = result["entries"], result["scan"]
    elapsed_from = time.monotonic()
    state = {"hashed_bytes": 0, "hashed_files": 0, "hash_attempts": 0, "stop_reason": None}

    def interrupted():
        if state["stop_reason"]:
            return True
        if cancel and cancel():
            state["stop_reason"] = "cancelled"
        elif time.monotonic() - elapsed_from >= limits.max_seconds:
            state["stop_reason"] = "time_limit"
        return bool(state["stop_reason"])

    def exclusion(entry_id, reason):
        if len(scan["exclusions"]) >= limits.max_entries:
            state["stop_reason"] = "exclusion_limit"
            return
        scan["exclusions"].append({"entry_id": entry_id, "reason": reason})

    def error(entry, exc):
        entry["status"] = "disappeared" if isinstance(exc, FileNotFoundError) else "unreadable"
        scan["errors"].append({"entry_id": entry["id"], "kind": type(exc).__name__, "errno": exc.errno})

    def hash_entry(parent_fd, name, entry):
        if not limits.hash_files:
            return
        digest_state = entry["hash"]
        digest_state["status"] = "skipped"
        size = entry["logical_bytes"]
        if size > limits.max_hash_file_bytes:
            digest_state["status"] = "file_byte_limit"
            return
        if (size > limits.max_hash_total_bytes - state["hashed_bytes"]
                or state["hash_attempts"] >= limits.max_hash_files):
            digest_state["status"] = "hash_budget_limit"
            return
        fd = None
        state["hash_attempts"] += 1
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or _fingerprint(before) != entry["fingerprint"]:
                digest_state["status"] = "stale"
                entry["status"] = "stale"
                return
            digest = hashlib.sha256()
            consumed = 0
            while consumed < size:
                if interrupted():
                    digest_state["status"] = "interrupted"
                    return
                chunk = os.read(fd, min(65536, size - consumed))
                if not chunk:
                    break
                consumed += len(chunk)
                state["hashed_bytes"] += len(chunk)
                digest.update(chunk)
            after = os.fstat(fd)
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (consumed != size or _fingerprint(after) != entry["fingerprint"]
                    or _fingerprint(current) != entry["fingerprint"]):
                digest_state["status"] = "stale"
                entry["status"] = "stale"
                return
            entry["hash"] = {"status": "verified", "algorithm": "sha256", "value": digest.hexdigest()}
            state["hashed_files"] += 1
        except OSError as exc:
            digest_state["status"] = "unreadable"
            error(entry, exc)
        finally:
            if fd is not None:
                os.close(fd)

    def invalidate_from(start):
        for descendant in entries[start:]:
            if descendant["status"] == "observed":
                descendant["status"] = "stale"
                descendant["uncertainties"].append("An ancestor changed during traversal.")
                if descendant["hash"]["status"] == "verified":
                    descendant["hash"]["status"] = "stale"
                    descendant["hash"]["value"] = None

    def visit_directory(fd, root_id, relative, depth, root_device, entry):
        if interrupted():
            return
        if depth >= limits.max_depth:
            exclusion(entry["id"], "depth_limit")
            return
        names = []
        try:
            with os.scandir(fd) as children:
                for child in children:
                    if interrupted():
                        return
                    names.append(child.name)
                    if len(names) > limits.max_directory_entries:
                        # Do not pick a non-deterministic subset from enumeration order.
                        exclusion(entry["id"], "directory_entry_limit")
                        return
        except OSError as exc:
            error(entry, exc)
            return
        for name in sorted(names):
            if interrupted():
                return
            if len(entries) >= limits.max_entries:
                state["stop_reason"] = "entry_limit"
                return
            child_relative = name if relative == "." else relative + "/" + name
            child_id = stable_id("entry", root_id, child_relative)
            if name in limits.exclude_names:
                entries.append(_entry(root_id, child_relative, status="excluded"))
                exclusion(child_id, "configured_name")
                continue
            try:
                observed = os.stat(name, dir_fd=fd, follow_symlinks=False)
                child = _entry(root_id, child_relative, observed)
            except OSError as exc:
                child = _entry(root_id, child_relative)
                entries.append(child)
                error(child, exc)
                continue
            entries.append(child)
            if child["kind"] in ("symlink", "special"):
                child["status"] = "unsupported"
                exclusion(child["id"], child["kind"] + "_not_followed")
            elif _placeholder(observed, name):
                child["status"] = "unsupported"
                child["hash"]["status"] = "placeholder_not_read"
                exclusion(child["id"], "known_placeholder_marker")
            elif not limits.cross_filesystems and observed.st_dev != root_device:
                child["status"] = "unsupported"
                exclusion(child["id"], "filesystem_boundary")
            elif child["kind"] == "directory":
                child_fd = None
                try:
                    child_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    if _fingerprint(os.fstat(child_fd)) != child["fingerprint"]:
                        child["status"] = "stale"
                        exclusion(child["id"], "changed_before_traversal")
                    else:
                        subtree_start = len(entries)
                        visit_directory(child_fd, root_id, child_relative, depth + 1, root_device, child)
                        if _fingerprint(os.fstat(child_fd)) != child["fingerprint"]:
                            child["status"] = "stale"
                            exclusion(child["id"], "changed_during_traversal")
                            invalidate_from(subtree_start)
                except OSError as exc:
                    error(child, exc)
                finally:
                    if child_fd is not None:
                        os.close(child_fd)
            else:
                hash_entry(fd, name, child)
            if progress:
                progress({"entries_observed": len(entries), "hashed_bytes": state["hashed_bytes"],
                          "status": "scanning"})

    for path in paths:
        root_id = stable_id("root", path)
        root = {"id": root_id, "path": path, "status": "pending", "identity": None}
        scan["roots"].append(root)
        if interrupted() or len(entries) >= limits.max_entries:
            root["status"] = "unvisited"
            if not state["stop_reason"]:
                state["stop_reason"] = "entry_limit"
            continue
        entry = _entry(root_id, ".")
        if not traversal_supported():
            entry["status"] = root["status"] = "unsupported"
            entries.append(entry)
            exclusion(entry["id"], "no_descriptor_relative_nofollow_traversal")
            continue
        root_fd = None
        try:
            root_fd = _open_root(path)
            observed = os.fstat(root_fd)
            entry = _entry(root_id, ".", observed)
            entries.append(entry)
            root["identity"] = entry["fingerprint"]
            subtree_start = len(entries)
            visit_directory(root_fd, root_id, ".", 0, observed.st_dev, entry)
            if (_fingerprint(os.fstat(root_fd)) != entry["fingerprint"]
                    or not _root_still_matches(path, entry["fingerprint"])):
                entry["status"] = "stale"
                exclusion(entry["id"], "root_or_ancestor_changed")
                invalidate_from(subtree_start)
            root["status"] = entry["status"]
        except OSError as exc:
            if entry not in entries:
                entries.append(entry)
            error(entry, exc)
            root["status"] = entry["status"]
        finally:
            if root_fd is not None:
                os.close(root_fd)
    observed_objects = {}
    inconsistent_objects = {e["object_id"] for e in entries
                            if e["kind"] == "file" and e["object_id"] and e["status"] == "stale"}
    for entry in entries:
        if entry["kind"] == "file" and entry["object_id"] and entry["status"] == "observed":
            prior = observed_objects.setdefault(entry["object_id"], entry["fingerprint"])
            if prior != entry["fingerprint"]:
                inconsistent_objects.add(entry["object_id"])
    for entry in entries:
        if entry["object_id"] in inconsistent_objects:
            entry["status"] = "stale"
            entry["uncertainties"].append("Conflicting metadata was observed for the same file object.")
            if entry["hash"]["status"] == "verified":
                entry["hash"].update(status="stale", value=None)
    entries.sort(key=lambda e: (e["root_id"], e["relative_path"]))
    scan["status"] = ("cancelled" if state["stop_reason"] == "cancelled" else
                      "partial" if state["stop_reason"] or scan["errors"] or scan["exclusions"]
                      or any(e["status"] != "observed" for e in entries) else "complete")
    scan["coverage"] = {"entries_observed": len(entries), "status_counts": dict(Counter(e["status"] for e in entries)),
                        "hashed_files": state["hashed_files"], "hash_attempts": state["hash_attempts"],
                        "hashed_bytes": state["hashed_bytes"],
                        "hash_status_counts": dict(Counter(e["hash"]["status"] for e in entries
                                                           if e["kind"] == "file")),
                        "stop_reason": state["stop_reason"], "atomic_snapshot": False,
                        "complete_within_policy": scan["status"] == "complete"}
    scan["id"] = stable_id("scan", scan_time, scan["roots"], entries, scan["coverage"])
    result["changes"] = compare_inventory(previous, result)
    from backend.disk_model_analysis import analyse_inventory
    result.update(analyse_inventory(result))
    if progress:
        progress({**scan["coverage"], "status": scan["status"]})
    return result


def compare_inventory(previous: dict | None, current: dict) -> dict:
    """Incremental metadata deltas; no removed entry is asserted after a partial scan."""
    before = {e["id"]: e for e in previous["entries"]} if previous else {}
    after = {e["id"]: e for e in current["entries"]}
    same_roots = previous is not None and {r["id"] for r in previous["scan"]["roots"]} == {
        r["id"] for r in current["scan"]["roots"]}
    old_roots = {r["id"]: r.get("identity") for r in previous["scan"]["roots"]} if previous else {}
    same_root_objects = bool(previous) and all(
        isinstance(old_roots.get(r["id"]), dict) and isinstance(r.get("identity"), dict)
        and all(old_roots[r["id"]].get(key) == r["identity"].get(key) for key in ("device", "inode"))
        for r in current["scan"]["roots"])
    same_policy = previous is not None and previous["scan"].get("limits") == current["scan"].get("limits")
    comparable = same_roots and same_root_objects and same_policy
    changed, unchanged = [], []
    for key in sorted(before.keys() & after.keys()):
        same_observation = (before[key]["fingerprint"] == after[key]["fingerprint"]
                            and before[key]["status"] == after[key]["status"])
        target = unchanged if same_observation else changed
        target.append(key)
    missing = sorted(before.keys() - after.keys())
    removed_observable = comparable and current["scan"]["status"] == "complete"
    return {"previous_scan_id": previous["scan"]["id"] if previous else None,
            "comparable": comparable, "added": sorted(after.keys() - before.keys()),
            "changed": changed, "unchanged_metadata": unchanged,
            "no_longer_observed": missing if removed_observable else [],
            "unverified_absent": [] if removed_observable else missing,
            "hashes_reused": 0,
            "uncertainties": ["Unchanged metadata does not prove unchanged content.",
                              "Entry IDs track root-relative addresses, not rename history."]}


def validate_inventory(model: dict) -> None:
    """Validate the complete contract and semantic references, never content authority."""
    from backend.disk_model_schema import validate_contract
    validate_contract(model)
    if (not isinstance(model, dict) or model.get("schema_version") != SCHEMA_VERSION
            or model.get("read_only") is not True or not isinstance(model.get("scan"), dict)
            or not isinstance(model.get("entries"), list) or len(model["entries"]) > 100000):
        raise ValueError("Unsupported inventory export")
    scan = model["scan"]
    if (not isinstance(scan.get("id"), str) or not isinstance(scan.get("roots"), list)
            or len(scan["roots"]) > 16 or not isinstance(scan.get("limits"), dict)):
        raise ValueError("Invalid scan identity or limits")
    root_ids = set()
    for root in scan["roots"]:
        if not isinstance(root, dict) or not isinstance(root.get("id"), str) or root["id"] in root_ids:
            raise ValueError("Invalid or repeated root ID")
        root_ids.add(root["id"])
    seen = set()
    for entry in model["entries"]:
        if (not isinstance(entry, dict) or not isinstance(entry.get("id"), str)
                or len(entry["id"]) > 128 or entry["id"] in seen):
            raise ValueError("Invalid or repeated entry ID")
        seen.add(entry["id"])
        relative = entry.get("relative_path")
        if (entry.get("root_id") not in root_ids or not isinstance(relative, str) or not relative
                or len(relative) > 65536 or relative.startswith("/") or "\0" in relative
                or ".." in relative.split("/")):
            raise ValueError("Invalid root-relative entry path")
        if (entry.get("kind") not in {"file", "directory", "symlink", "special", "unknown"}
                or entry.get("status") not in {"observed", "stale", "disappeared", "unreadable",
                                               "unsupported", "excluded"}
                or "fingerprint" not in entry):
            raise ValueError("Invalid entry kind, status or fingerprint")
        for key in ("logical_bytes", "allocated_bytes"):
            value = entry.get(key)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Invalid byte observation")
        if entry["kind"] == "file" and entry.get("logical_bytes") is None:
            raise ValueError("Regular file lacks a logical size")

    def unique_records(records, key="id"):
        ids = [record[key] for record in records]
        if len(set(ids)) != len(ids):
            raise ValueError("Repeated contract record ID")
        return set(ids)

    def references(values, allowed):
        if len(values) != len(set(values)) or not set(values) <= allowed:
            raise ValueError("Invalid or repeated contract reference")

    evidence_ids = unique_records(model["evidence"])
    finding_ids = unique_records(model["findings"])
    unique_records(model["relationships"])
    unique_records(model["plan_alternatives"])
    unique_records(model["directories"], "entry_id")
    for entry in model["entries"]:
        if entry["parent_id"] is not None and entry["parent_id"] not in seen:
            raise ValueError("Unknown parent entry")
    for evidence in model["evidence"]:
        references(evidence["member_ids"], seen)
    for found in model["findings"] + model["relationships"]:
        references(found["member_ids"], seen)
        references(found["evidence_ids"], evidence_ids)
    for directory in model["directories"]:
        references([directory["entry_id"]], seen)
        references(directory["direct_member_ids"], seen)
        for role in directory["role_hypotheses"]:
            references(role["evidence_ids"], evidence_ids)
    for plan in model["plan_alternatives"]:
        references(plan["finding_ids"], finding_ids)
        references(plan["scope_member_ids"], seen)
        scope = set(plan["scope_member_ids"])
        for alternative in plan["alternatives"]:
            references(alternative["unchanged_member_ids"], scope)
            references(alternative["uncertain_member_ids"], scope)
            if set(alternative["unchanged_member_ids"]) != scope:
                raise ValueError("Read-only alternatives must preserve every scoped member")
            steps = set()
            for step in alternative["steps"]:
                references(step["depends_on"], steps)
                references(step["member_ids"], scope)
                references(step["evidence_ids"], evidence_ids)
                if step["id"] in steps:
                    raise ValueError("Repeated alternative step")
                steps.add(step["id"])


def query_entries(model: dict, *, root_id: str | None = None, kind: str | None = None,
                  status: str | None = None, path_contains: str = "", min_bytes: int = 0,
                  offset: int = 0, limit: int = 100) -> dict:
    """Bounded deterministic projection. Filtering never changes model totals."""
    validate_inventory(model)
    if type(limit) is not int or not 1 <= limit <= 1000 or type(offset) is not int or offset < 0:
        raise ValueError("limit must be 1–1000 and offset non-negative")
    if type(min_bytes) is not int or min_bytes < 0:
        raise ValueError("min_bytes must be non-negative")
    matching = [e for e in model["entries"] if (not root_id or e["root_id"] == root_id)
                and (not kind or e["kind"] == kind) and (not status or e["status"] == status)
                and path_contains.casefold() in e["relative_path"].casefold()
                and (e["logical_bytes"] or 0) >= min_bytes]
    matching.sort(key=lambda e: (e["root_id"], e["relative_path"]))
    return {"scan_id": model["scan"]["id"], "total_matching": len(matching), "offset": offset,
            "entries": matching[offset:offset + limit],
            "next_offset": offset + limit if offset + limit < len(matching) else None}


def export_json(model: dict) -> str:
    return json.dumps(model, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + "\n"
