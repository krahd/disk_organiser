"""Pure synthetic Disk Model observations to an explicitly incomplete review draft.

No scan, path lookup, provider, executor or existing planner review is called.
An observed root is not a physical volume; this draft cannot certify a copy/no-op.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter
from datetime import datetime

from backend.disk_model import validate_inventory


DRAFT_VERSION = "disk-administration-observation-draft/v1"
MAX_ENTRIES = 2000
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_JSON_NODES = 100000
MAX_DEPTH = 32
MAX_COLLISION_CHECKS = 1_000_000
MAX_ISSUES = 512


class AdapterError(ValueError):
    """The supplied synthetic observations or explicit decision are not admissible."""


def _bounded_json(value):
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > MAX_JSON_NODES or depth > MAX_DEPTH:
            raise AdapterError("Input exceeds the adapter's structural bounds")
        if type(item) in (dict, list) and count + len(pending) + len(item) > MAX_JSON_NODES:
            raise AdapterError("Input exceeds the adapter's structural bounds")
        if type(item) is dict:
            if any(type(key) is not str or len(key) > 256 for key in item):
                raise AdapterError("Expected bounded JSON object keys")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            if len(item) > 4096:
                raise AdapterError("Text exceeds the adapter limit")
        elif item is not None and type(item) not in (bool, int, float):
            raise AdapterError("Expected JSON data only")
        elif type(item) is float and not math.isfinite(item):
            raise AdapterError("Non-finite values are unsupported")
        elif type(item) is int and abs(item) > 2**63 - 1:
            raise AdapterError("Integer exceeds the adapter limit")
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_JSON_BYTES:
        raise AdapterError("Input exceeds the adapter byte limit")
    return encoded


def _time(value):
    _text(value)
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AdapterError("Invalid timestamp") from error
    if stamp.tzinfo is None:
        raise AdapterError("Timestamp requires a timezone")
    return stamp


def _text(value):
    if not isinstance(value, str) or not value or len(value) > 4096 or any(ord(c) < 32 for c in value):
        raise AdapterError("Expected bounded non-empty text")
    return value


def _path(value):
    _text(value)
    if value.startswith("/") or "\\" in value or ":" in value or any(p in ("", ".", "..") for p in value.split("/")):
        raise AdapterError("Expected a portable project-relative address")
    return value


def _keys(value, fields):
    if type(value) is not dict or set(value) != set(fields.split()):
        raise AdapterError("Missing or unsupported decision fields")


def _overlap(first, second):
    return first == second or first.startswith(second + "/") or second.startswith(first + "/")


def _validate_observation(model):
    encoded = _bounded_json(model)
    if type(model) is not dict or model.get("synthetic") is not True:
        raise AdapterError("Only explicitly synthetic Disk Model exports are accepted")
    if not isinstance(model.get("entries"), list) or len(model["entries"]) > MAX_ENTRIES:
        raise AdapterError("Observation entry count exceeds the adapter limit")
    try:
        validate_inventory(model)
    except (ValueError, TypeError, KeyError) as error:
        raise AdapterError("Invalid canonical Disk Model export") from error
    entries = {entry["id"]: entry for entry in model["entries"]}
    addresses = {}
    aliases = {}
    for entry in entries.values():
        address = (entry["root_id"], entry["relative_path"])
        if address in addresses:
            raise AdapterError("Repeated observed address")
        addresses[address] = entry
        relative = entry["relative_path"]
        if relative != ".":
            _path(relative)
            parent_path = relative.rsplit("/", 1)[0] if "/" in relative else "."
            parent = entries.get(entry["parent_id"])
            if (parent is None or parent["root_id"] != entry["root_id"] or
                    parent["relative_path"] != parent_path or parent["kind"] != "directory"):
                raise AdapterError("Contradictory observed parent/address structure")
        elif entry["parent_id"] is not None or entry["kind"] not in ("directory", "unknown"):
            raise AdapterError("Invalid root entry")
        if entry["hash"]["status"] == "verified" and (entry["kind"] != "file" or entry["status"] != "observed"):
            raise AdapterError("Contradictory recorded hash state")
        if entry["object_id"] is not None:
            aliases.setdefault(entry["object_id"], []).append(entry)
    for group in aliases.values():
        first = group[0]
        for entry in group[1:]:
            if any(entry[key] != first[key] for key in
                   ("kind", "logical_bytes", "allocated_bytes", "link_count", "fingerprint")):
                raise AdapterError("Conflicting observed object aliases")
        recorded_hashes = {entry["hash"]["value"] for entry in group if entry["hash"]["status"] == "verified"}
        if len(recorded_hashes) > 1:
            raise AdapterError("Conflicting recorded hashes for an observed object")
    scan = model["scan"]
    for root in scan["roots"]:
        root_entry = addresses.get((root["id"], "."))
        if root_entry is None:
            if root["status"] not in ("pending", "unvisited"):
                raise AdapterError("Observed root entry is missing")
        elif (root["status"] != root_entry["status"] or
              (root["identity"] is not None and root_entry["fingerprint"] is not None and
               root["identity"] != root_entry["fingerprint"])):
            raise AdapterError("Contradictory root observation")
    coverage = scan["coverage"]
    if (coverage["entries_observed"] != len(entries) or
            coverage["status_counts"] != dict(Counter(e["status"] for e in entries.values())) or
            coverage["hash_status_counts"] != dict(Counter(e["hash"]["status"] for e in entries.values() if e["kind"] == "file")) or
            coverage["hashed_files"] != sum(e["hash"]["status"] == "verified" for e in entries.values())):
        raise AdapterError("Contradictory observation coverage")
    if coverage["complete_within_policy"] != (scan["status"] == "complete"):
        raise AdapterError("Contradictory scan completion")
    if scan["status"] == "complete" and (scan["errors"] or scan["exclusions"] or coverage["stop_reason"] is not None or
                                         any(e["status"] != "observed" for e in entries.values()) or
                                         any(r["status"] != "observed" for r in scan["roots"])):
        raise AdapterError("Incomplete observations cannot be labelled complete")
    if (scan["status"] == "cancelled") != (coverage["stop_reason"] == "cancelled"):
        raise AdapterError("Contradictory cancellation state")
    changes = model["changes"]
    current_changes = [changes[key] for key in ("added", "changed", "unchanged_metadata")]
    reported_current = [identifier for group in current_changes for identifier in group]
    absent = changes["no_longer_observed"] + changes["unverified_absent"]
    if (len(set(reported_current)) != len(reported_current) or not set(reported_current) <= set(entries) or
            len(set(absent)) != len(absent) or set(absent) & set(entries)):
        raise AdapterError("Contradictory reported change scope")
    if changes["no_longer_observed"] and (scan["status"] != "complete" or changes["comparable"] is not True):
        raise AdapterError("Incomplete or incomparable observations cannot establish absence")
    return hashlib.sha256(encoded).hexdigest()


def observation_digest(model):
    """Bounded synthetic snapshot revision, never authentication or identity proof."""
    return _validate_observation(model)


def build_observation_draft(model, decision, *, expected_observation_digest, now,
                            max_observation_age_hours=2):
    """Adapt explicit member/path intent; missing facts stay missing and blocking."""
    snapshot_digest = _validate_observation(model)
    if not isinstance(expected_observation_digest, str) or expected_observation_digest != snapshot_digest:
        raise AdapterError("Stale observation reference")
    _bounded_json(decision)
    _keys(decision, "project_id project_label member_paths destination_root_id destination_folder acknowledged")
    _text(decision["project_id"])
    _text(decision["project_label"])
    _path(decision["destination_folder"])
    if type(decision["acknowledged"]) is not bool:
        raise AdapterError("Expected an explicit review acknowledgement")
    if type(max_observation_age_hours) is not int or not 1 <= max_observation_age_hours <= 24 * 365:
        raise AdapterError("Invalid observation-age bound")
    evaluated_at = _time(now)
    scan = model["scan"]
    age = (evaluated_at - _time(scan["started_at"])).total_seconds()
    freshness = "future" if age < 0 else "stale" if age > max_observation_age_hours * 3600 else "within_requested_window"
    roots = {root["id"]: root for root in scan["roots"]}
    entries = {entry["id"]: entry for entry in model["entries"]}
    if not isinstance(decision["destination_root_id"], str) or decision["destination_root_id"] not in roots:
        raise AdapterError("Unknown intended observation root")
    member_paths = decision["member_paths"]
    if type(member_paths) is not list or not 1 <= len(member_paths) <= MAX_ENTRIES:
        raise AdapterError("Select bounded explicit members")
    selected = {}
    for member in member_paths:
        _keys(member, "entry_id project_path")
        identifier = member["entry_id"]
        if not isinstance(identifier, str) or identifier not in entries or identifier in selected:
            raise AdapterError("Unknown or repeated selected member")
        selected[identifier] = _path(member["project_path"])
    selected_ids = sorted(selected)
    destination_root = decision["destination_root_id"]
    scoped_roots = sorted({destination_root, *(entries[identifier]["root_id"] for identifier in selected_ids)})
    blockers = []
    issue_keys = set()

    def block(code, member_ids=(), root_ids=()):
        members_key, roots_key = tuple(sorted(set(member_ids))), tuple(sorted(set(root_ids)))
        key = (code, members_key, roots_key)
        if key not in issue_keys:
            if len(blockers) >= MAX_ISSUES:
                raise AdapterError("Draft issue budget exceeded; reduce selected scope")
            issue_keys.add(key)
            blockers.append({"code": code, "member_ids": list(members_key), "root_ids": list(roots_key)})

    for code in ("physical_volume_identity_unestablished", "volume_name_semantics_unknown", "current_root_availability_unverified"):
        block(code, selected_ids, scoped_roots)
    for code in ("content_version_unverified", "project_dependencies_unknown", "backup_evidence_unavailable", "restore_evidence_unavailable"):
        block(code, selected_ids)
    block("destination_capacity_unknown", (), [destination_root])
    if not decision["acknowledged"]:
        block("membership_and_destination_need_review", selected_ids)
    if freshness != "within_requested_window":
        block("observation_" + freshness, selected_ids, scoped_roots)
    if scan["status"] != "complete":
        block("observation_scope_incomplete", selected_ids, scoped_roots)
    for root_id in scoped_roots:
        if roots[root_id]["status"] != "observed":
            block("root_not_observed", (), [root_id])
    members = []
    proposed = {}
    occupied = [e for e in entries.values() if e["root_id"] == destination_root]
    comparisons = len(selected_ids) * (len(selected_ids) - 1) // 2 + len(selected_ids) * len(occupied)
    if comparisons > MAX_COLLISION_CHECKS:
        raise AdapterError("Draft collision-comparison budget exceeded; reduce selected scope")
    known_bytes = 0
    unknown_sizes = []
    for identifier in selected_ids:
        entry = entries[identifier]
        target_path = _path(decision["destination_folder"] + "/" + selected[identifier])
        same_address = entry["root_id"] == destination_root and entry["relative_path"] == target_path
        if entry["status"] != "observed":
            block("member_not_observed", [identifier], [entry["root_id"]])
        if entry["kind"] != "file":
            block("unsupported_member_kind", [identifier])
        if entry["hash"]["status"] == "placeholder_not_read":
            block("placeholder_content_unavailable", [identifier])
        if entry["link_count"] != 1:
            block("link_identity_unresolved", [identifier])
        if entry["logical_bytes"] is None:
            unknown_sizes.append(identifier)
        else:
            known_bytes += entry["logical_bytes"]
        for other_path, other_id in proposed.items():
            if _overlap(target_path, other_path):
                block("declared_project_path_collision", [identifier, other_id])
        proposed[target_path] = identifier
        for other in occupied:
            existing = other["relative_path"]
            overlaps = (_overlap(target_path, existing) if other["kind"] != "directory" else
                        existing == target_path or existing.startswith(target_path + "/"))
            if overlaps:
                block("observed_target_path_overlap", [identifier, other["id"]], [destination_root])
        members.append({"entry_id": identifier, "project_path": selected[identifier],
                        "source": {"root_id": entry["root_id"], "relative_path": entry["relative_path"]},
                        "intended": {"root_id": destination_root, "relative_path": target_path},
                        "placement": "current_address_requires_identity" if same_address else "proposed_address_requires_review",
                        "observation": copy.deepcopy(entry), "volume_id": None, "content_version": None,
                        "dependency_coverage": "unknown", "source_retained": True})
    return {"schema_version": DRAFT_VERSION, "synthetic": True, "read_only": True,
            "executable": False, "execution_authority": None, "undo_available": False,
            "source_safe_to_erase": False, "status": "blocked_observation_draft",
            "observation_digest": snapshot_digest,
            "decision_digest": hashlib.sha256(_bounded_json(decision)).hexdigest(),
            "evaluated_at": now, "max_observation_age_hours": max_observation_age_hours,
            "recorded_scan_freshness": freshness,
            "project": {"id": decision["project_id"], "label": decision["project_label"]},
            "member_ids": selected_ids, "members": members,
            "observed_roots": copy.deepcopy(sorted(scan["roots"], key=lambda root: root["id"])),
            "observation_scope": {"scan": copy.deepcopy(scan), "reported_changes": copy.deepcopy(model["changes"]),
                                  "analysis_coverage": copy.deepcopy(model["analysis_coverage"]),
                                  "entry_count": len(entries), "selected_entry_count": len(selected_ids)},
            "blockers": blockers,
            "capacity": {"known_recorded_path_logical_bytes": known_bytes, "unknown_size_member_ids": unknown_sizes,
                         "known_logical_copy_bytes": None, "required_destination_bytes": None,
                         "observed_free_bytes": None, "physical_allocation_prediction": None, "reclaimed_bytes": 0},
            "protection": {"configured_target_ids": None, "independent_copy_count": None,
                           "project_restore_satisfied": None, "live_backup_verified": False, "live_restore_verified": False},
            "limitations": ["Synthetic observations and root fingerprints do not authenticate physical volumes or current files.",
                            "Root labels, address IDs, hashes and object aliases do not establish volume identity or independent protection.",
                            "Recorded logical bytes count selected paths, including aliases; they are not required copy space or physical allocation.",
                            "Role, project and duplicate hypotheses never select members or confirm dependencies.",
                            "Snapshot freshness is measured from its recorded start time, not per-entry observation or live availability.",
                            "A complete scan is bounded by its recorded policy and is not an atomic whole-drive snapshot.",
                            "Missing members after partial or unavailable observations are not confirmed deletions.",
                            "This incomplete draft is not a planner review and cannot establish a copy, no-op, backup, restore or execution permission."]}
