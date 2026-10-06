"""Synthetic-only organisation/protection review. No filesystem or network I/O.

This is a product-contract prototype, not a scanner, backup client or executor.
Importing this module does not import any existing Disk Organiser mutation code.
"""

from __future__ import annotations

import copy
import hashlib
import json
import unicodedata
from datetime import datetime


INPUT_VERSION = "disk-administration-synthetic/v1"
OUTPUT_VERSION = "disk-administration-review/v1"
MAX_ITEMS = 2000
MAX_JSON_BYTES = 4 * 1024 * 1024


class ContractError(ValueError):
    """An input cannot be safely interpreted as this prototype's contract."""


def _keys(value, required):
    if not isinstance(value, dict) or set(value) != set(required.split()):
        raise ContractError("Missing or unsupported object fields")


def _text(value):
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise ContractError("Expected bounded non-empty text")
    if any(ord(char) < 32 for char in value):
        raise ContractError("Control characters are unsupported")
    return value


def _choice(value, allowed):
    if value not in allowed:
        raise ContractError("Unsupported enum value")


def _integer(value, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not int or value < 0 or value > 2**63 - 1:
        raise ContractError("Expected a bounded non-negative integer")


def _bool(value):
    if type(value) is not bool:
        raise ContractError("Expected a boolean")


def _time(value):
    _text(value)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError("Invalid timestamp") from error
    if result.tzinfo is None:
        raise ContractError("Timestamp requires an explicit timezone")
    return result


def _path(value):
    _text(value)
    # Portable relative addresses only. This does not resolve or open a path.
    if "\\" in value or ":" in value or value.startswith("/"):
        raise ContractError("Expected a portable relative address")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ContractError("Ambiguous or traversing address")
    return value


def _list(value):
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise ContractError("Expected a bounded list")
    return value


def _unique_strings(value):
    values = _list(value)
    for item in values:
        _text(item)
    if len(set(values)) != len(values):
        raise ContractError("Duplicate references")


def _index(values):
    result = {}
    for value in _list(values):
        if not isinstance(value, dict):
            raise ContractError("Expected an object")
        identifier = _text(value.get("id"))
        if identifier in result:
            raise ContractError("Duplicate record identity")
        result[identifier] = value
    return result


def digest(document):
    """Revision identifier only. A digest does not confer operation authority."""
    try:
        encoded = json.dumps(document, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as error:
        raise ContractError("Input is not canonical JSON data") from error
    if len(encoded) > MAX_JSON_BYTES:
        raise ContractError("Input exceeds the bounded prototype size")
    return hashlib.sha256(encoded).hexdigest()


def loads(text):
    """Reject duplicate JSON fields, non-finite values and oversized input."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_JSON_BYTES:
        raise ContractError("Invalid or oversized JSON")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ContractError("Duplicate JSON field")
            result[key] = value
        return result

    def constant(_value):
        raise ContractError("Non-finite JSON number")

    try:
        result = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, RecursionError) as error:
        raise ContractError("Invalid JSON") from error
    validate(result)
    return result


def validate(document):
    """Strict synthetic contract. Imported assertions never become live proof."""
    _keys(document, "schema_version synthetic now revision volumes entries project decision targets policy backups restores")
    if document["schema_version"] != INPUT_VERSION or document["synthetic"] is not True:
        raise ContractError("Only the explicit synthetic v1 contract is supported")
    _time(document["now"])
    _integer(document["revision"])
    digest(document)
    volumes = _index(document["volumes"])
    entries = _index(document["entries"])
    targets = _index(document["targets"])
    backups = _index(document["backups"])
    _index(document["restores"])
    for volume in volumes.values():
        _keys(volume, "id label state observed_at coverage case_sensitive unicode_normalization free_bytes failure_domain")
        _text(volume["label"])
        _choice(volume["state"], ("online", "offline", "unknown"))
        _time(volume["observed_at"])
        _choice(volume["coverage"], ("complete", "partial", "unknown"))
        _choice(volume["case_sensitive"], (True, False, None))
        if volume["case_sensitive"] is not None:
            _bool(volume["case_sensitive"])
        _choice(volume["unicode_normalization"], ("NFC", "NFD", "unknown"))
        _integer(volume["free_bytes"], nullable=True)
        if volume["failure_domain"] is not None:
            _text(volume["failure_domain"])
    source_addresses = set()
    for entry in entries.values():
        _keys(entry, "id volume_id path project_path kind bytes version observed_at dependencies dependency_coverage link_count")
        if entry["volume_id"] not in volumes:
            raise ContractError("Unknown entry volume")
        _path(entry["path"])
        _path(entry["project_path"])
        source_address = (entry["volume_id"], _normalise(entry["path"], volumes[entry["volume_id"]]))
        if source_address in source_addresses:
            raise ContractError("Ambiguous duplicate source address")
        source_addresses.add(source_address)
        _choice(entry["kind"], ("file", "symlink", "placeholder", "bundle", "unknown"))
        _integer(entry["bytes"], nullable=True)
        if entry["version"] is not None:
            _text(entry["version"])
        _time(entry["observed_at"])
        _unique_strings(entry["dependencies"])
        # Unknown dependency IDs are valid observations and become blockers.
        _choice(entry["dependency_coverage"], ("declared_complete", "unknown"))
        _integer(entry["link_count"], nullable=True)
    project = document["project"]
    _keys(project, "id label candidate_member_ids")
    _text(project["id"])
    _text(project["label"])
    _unique_strings(project["candidate_member_ids"])
    if any(identifier not in entries for identifier in project["candidate_member_ids"]):
        raise ContractError("Unknown proposed project member")
    decision = document["decision"]
    _keys(decision, "member_ids destination_volume_id destination_folder acknowledged")
    _unique_strings(decision["member_ids"])
    if not decision["member_ids"] or any(identifier not in entries for identifier in decision["member_ids"]):
        raise ContractError("Project needs known selected members")
    if decision["destination_volume_id"] not in volumes:
        raise ContractError("Unknown intended destination")
    _path(decision["destination_folder"])
    _bool(decision["acknowledged"])
    for target in targets.values():
        _keys(target, "id label kind failure_domain region")
        _text(target["label"])
        _choice(target["kind"], ("local", "object_storage", "managed_backup", "sync"))
        for field in ("failure_domain", "region"):
            if target[field] is not None:
                _text(target[field])
    policy = document["policy"]
    _keys(policy, "target_ids max_evidence_age_hours max_restore_age_hours max_inventory_age_hours required_independent_copies require_project_restore required_restore_check reserve_bytes")
    _unique_strings(policy["target_ids"])
    if any(identifier not in targets for identifier in policy["target_ids"]):
        raise ContractError("Unknown configured target")
    for field in ("max_evidence_age_hours", "max_restore_age_hours", "max_inventory_age_hours", "required_independent_copies", "reserve_bytes"):
        _integer(policy[field])
    if any(policy[field] == 0 for field in ("max_evidence_age_hours", "max_restore_age_hours", "max_inventory_age_hours", "required_independent_copies")):
        raise ContractError("Policy evidence windows and copy count must be positive")
    _bool(policy["require_project_restore"])
    _choice(policy["required_restore_check"], ("bytes", "bytes_and_app"))
    for backup in backups.values():
        _keys(backup, "id target_id snapshot_id observed_at level complete entry_versions")
        if backup["target_id"] not in targets:
            raise ContractError("Unknown evidence target")
        _text(backup["snapshot_id"])
        _time(backup["observed_at"])
        _choice(backup["level"], ("declared_configuration", "provider_report", "manifest_verified", "content_verified"))
        _bool(backup["complete"])
        _versions(backup["entry_versions"], entries)
    for restore in document["restores"]:
        _keys(restore, "id backup_id completed_at scope outcome check entry_versions")
        if restore["backup_id"] not in backups:
            raise ContractError("Restore must reference a known backup record")
        _time(restore["completed_at"])
        _choice(restore["scope"], ("sample", "project"))
        _choice(restore["outcome"], ("passed", "failed", "unknown"))
        _choice(restore["check"], ("bytes", "bytes_and_app"))
        _versions(restore["entry_versions"], entries)
    return document


def _versions(value, entries):
    if not isinstance(value, dict) or len(value) > MAX_ITEMS:
        raise ContractError("Invalid member-version manifest")
    for identifier, version in value.items():
        if identifier not in entries:
            raise ContractError("Unknown manifest member")
        _text(version)


def _fresh(observed_at, now, hours):
    age = (_time(now) - _time(observed_at)).total_seconds()
    return 0 <= age <= hours * 3600


def _normalise(path, volume):
    normalisation = volume["unicode_normalization"]
    form = normalisation if normalisation != "unknown" else "NFC"
    if volume["case_sensitive"] is True:
        return unicodedata.normalize(form, path)
    # Canonical decomposition must precede folding (Unicode D145), including
    # U+0345 cases where starting with NFC does not preserve equivalence.
    value = unicodedata.normalize("NFD", path).casefold()
    return unicodedata.normalize(form, value)


def _overlap(first, second):
    return first == second or first.startswith(second + "/") or second.startswith(first + "/")


def review(document):
    """Return immutable-by-convention, exact-scope, explicitly non-executable data."""
    validate(document)
    now = document["now"]
    policy = document["policy"]
    volumes = _index(document["volumes"])
    entries = _index(document["entries"])
    targets = _index(document["targets"])
    decision = document["decision"]
    selected = sorted(decision["member_ids"])
    destination = volumes[decision["destination_volume_id"]]
    blockers = []

    def block(code, members=()):
        item = {"code": code, "member_ids": sorted(set(members))}
        if item not in blockers:
            blockers.append(item)

    if not decision["acknowledged"]:
        block("membership_and_destination_need_review", selected)
    if destination["state"] != "online":
        block("destination_not_online")
    if destination["coverage"] != "complete":
        block("destination_coverage_incomplete")
    if not _fresh(destination["observed_at"], now, policy["max_inventory_age_hours"]):
        block("destination_observation_stale_or_future")
    if destination["case_sensitive"] is None or destination["unicode_normalization"] == "unknown":
        block("destination_name_semantics_unknown")

    changes = []
    total = 0
    unknown_sizes = []
    for identifier in selected:
        entry = entries[identifier]
        volume = volumes[entry["volume_id"]]
        if volume["state"] != "online":
            block("source_not_online", [identifier])
        if volume["coverage"] != "complete":
            block("source_coverage_incomplete", [identifier])
        if volume["case_sensitive"] is None or volume["unicode_normalization"] == "unknown":
            block("source_name_semantics_unknown", [identifier])
        if not _fresh(volume["observed_at"], now, policy["max_inventory_age_hours"]):
            block("source_volume_observation_stale_or_future", [identifier])
        if not _fresh(entry["observed_at"], now, policy["max_inventory_age_hours"]):
            block("source_observation_stale_or_future", [identifier])
        if entry["kind"] != "file":
            block("unsupported_" + entry["kind"], [identifier])
        if entry["link_count"] != 1:
            block("hardlink_or_link_identity_unknown", [identifier])
        if entry["version"] is None:
            block("source_version_unknown", [identifier])
        if entry["dependency_coverage"] != "declared_complete":
            block("project_dependencies_unknown", [identifier])
        missing = set(entry["dependencies"]) - set(selected)
        if missing:
            block("project_dependency_not_selected", [identifier, *missing])
        if entry["bytes"] is None:
            unknown_sizes.append(identifier)
        else:
            total += entry["bytes"]
        source_path = _normalise(entry["path"], volume)
        for other_id, other_entry in entries.items():
            if other_id == identifier or other_entry["volume_id"] != entry["volume_id"]:
                continue
            ancestor = _normalise(other_entry["path"], volume)
            # v1 models file-like entries only. A declared file/link/package
            # cannot be silently treated as a traversable source directory.
            if _overlap(source_path, ancestor):
                block("source_ancestor_not_a_directory", [identifier, other_id])
        target_path = decision["destination_folder"] + "/" + entry["project_path"]
        changes.append({"member_id": identifier, "proposal": "copy_with_project_structure",
                        "source": {"volume_id": entry["volume_id"], "relative_path": entry["path"], "version": entry["version"]},
                        "destination": {"volume_id": destination["id"], "relative_path": target_path},
                        "source_retained": True})

    proposed = {}
    occupied = [(identifier, _normalise(entry["path"], destination))
                for identifier, entry in entries.items() if entry["volume_id"] == destination["id"]]
    for change in changes:
        target_path = _normalise(change["destination"]["relative_path"], destination)
        for other_path, other_member in proposed.items():
            if _overlap(target_path, other_path):
                block("planned_name_or_ancestor_collision", [change["member_id"], other_member])
        proposed[target_path] = change["member_id"]
        for other_member, existing_path in occupied:
            if _overlap(target_path, existing_path):
                block("occupied_name_or_ancestor_collision", [change["member_id"], other_member])
        # Conservative portable destination screen; platform adapter must do more.
        for part in change["destination"]["relative_path"].split("/"):
            base = part.split(".")[0].upper()
            if part.endswith((" ", ".")) or any(char in '<>"|?*' for char in part) or base in {"CON", "PRN", "AUX", "NUL", *("COM" + str(n) for n in range(1, 10)), *("LPT" + str(n) for n in range(1, 10))}:
                block("nonportable_destination_name", [change["member_id"]])
    if unknown_sizes:
        block("required_capacity_unknown", unknown_sizes)
    required = None if unknown_sizes else total + policy["reserve_bytes"]
    if destination["free_bytes"] is None:
        block("destination_capacity_unknown")
    elif required is not None and required > destination["free_bytes"]:
        block("insufficient_observed_capacity")

    # Later contradictory evidence for one target/snapshot supersedes an older
    # success. Tied latest timestamps are ambiguous; never silently pick one.
    evidence_groups = {}
    for backup in document["backups"]:
        key = (backup["target_id"], backup["snapshot_id"])
        evidence_groups.setdefault(key, []).append(backup)
    current_evidence_ids = set()
    for group in evidence_groups.values():
        newest = max(_time(item["observed_at"]) for item in group)
        latest = [item for item in group if _time(item["observed_at"]) == newest]
        if len(latest) == 1:
            current_evidence_ids.add(latest[0]["id"])
        elif latest[0]["target_id"] in policy["target_ids"]:
            block("ambiguous_latest_backup_evidence", selected)

    protection = []
    eligible_by_id = {}
    for identifier in selected:
        entry = entries[identifier]
        source_domain = volumes[entry["volume_id"]]["failure_domain"]
        observations = []
        independent_domains = set()
        eligible_by_id[identifier] = []
        for backup in sorted(document["backups"], key=lambda item: item["id"]):
            if backup["target_id"] not in policy["target_ids"]:
                continue
            target = targets[backup["target_id"]]
            matches = entry["version"] is not None and backup["entry_versions"].get(identifier) == entry["version"]
            fresh = _fresh(backup["observed_at"], now, policy["max_evidence_age_hours"])
            independent = source_domain is not None and target["failure_domain"] is not None and target["failure_domain"] != source_domain
            verified = matches and fresh and backup["complete"] and backup["level"] == "content_verified" and target["kind"] != "sync"
            current = backup["id"] in current_evidence_ids
            eligible = verified and independent and current
            observations.append({"backup_id": backup["id"], "target_id": target["id"], "evidence_level": backup["level"],
                                 "snapshot_id": backup["snapshot_id"], "observed_at": backup["observed_at"],
                                 "matches_current_fixture_version": matches, "fresh": fresh, "complete": backup["complete"],
                                 "current_snapshot_evidence": current,
                                 "independent_declared_domain": independent, "counts_for_fixture_copy_requirement": eligible})
            if eligible:
                independent_domains.add(target["failure_domain"])
                eligible_by_id[identifier].append(backup["id"])
        satisfies = len(independent_domains) >= policy["required_independent_copies"]
        if not satisfies:
            block("verified_independent_copy_requirement_unmet", [identifier])
        protection.append({"member_id": identifier, "observations": observations,
                           "independent_fixture_copy_domains": len(independent_domains), "policy_satisfied_in_fixture": satisfies})

    backup_records = _index(document["backups"])
    restore_histories = {}
    for restore in document["restores"]:
        record = backup_records[restore["backup_id"]]
        key = (record["target_id"], record["snapshot_id"])
        restore_histories.setdefault(key, []).append(restore)

    def full_current_success(restore, required_check):
        covered = all(entries[identifier]["version"] is not None and
                      restore["entry_versions"].get(identifier) == entries[identifier]["version"]
                      for identifier in selected)
        backing = all(restore["backup_id"] in eligible_by_id[identifier] for identifier in selected)
        method = required_check == "bytes" or restore["check"] == "bytes_and_app"
        return (restore["outcome"] == "passed" and restore["scope"] == "project" and
                covered and backing and method and _time(restore["completed_at"]) <= _time(now))

    # Retain invalidation events throughout history, not just the latest event.
    # A later sample cannot dominate a whole-project failure or an ambiguous
    # earlier time group. Resolution is deliberately conservative: a later full
    # current-project success with at least the invalidation's check method.
    invalidations = {}
    restore_alerts = []
    for snapshot_key, history in restore_histories.items():
        by_time = {}
        for event in history:
            by_time.setdefault(_time(event["completed_at"]), []).append(event)
        invalidations[snapshot_key] = []
        for timestamp, events in sorted(by_time.items()):
            reasons = []
            if len(events) > 1:
                reasons.append("ambiguous_timestamp")
            if timestamp > _time(now):
                reasons.append("future_timestamp")
            if any(event["outcome"] != "passed" for event in events):
                reasons.append("failed_or_unknown_outcome")
            if not reasons:
                continue
            required_check = "bytes_and_app" if any(event["check"] == "bytes_and_app" for event in events) else "bytes"
            resolved = any(_time(success["completed_at"]) > timestamp and
                           len(by_time[_time(success["completed_at"])]) == 1 and
                           full_current_success(success, required_check) for success in history)
            event = {"at": timestamp, "required_check": required_check, "resolved": resolved,
                     "event_ids": sorted(item["id"] for item in events), "reasons": reasons}
            invalidations[snapshot_key].append(event)
            if not resolved and snapshot_key[0] in policy["target_ids"]:
                block("unresolved_restore_evidence_requires_attention", selected)
                restore_alerts.append({"target_id": snapshot_key[0], "snapshot_id": snapshot_key[1],
                                       "at": timestamp.isoformat(), "required_check": required_check,
                                       "member_ids": selected, "event_ids": event["event_ids"], "reasons": reasons})
    restore_results = []
    project_restore = False
    for restore in sorted(document["restores"], key=lambda item: item["id"]):
        covered = [identifier for identifier in selected if entries[identifier]["version"] is not None and restore["entry_versions"].get(identifier) == entries[identifier]["version"]]
        fresh = _fresh(restore["completed_at"], now, policy["max_restore_age_hours"])
        record = backup_records[restore["backup_id"]]
        snapshot_key = (record["target_id"], record["snapshot_id"])
        invalidated = any(event["at"] >= _time(restore["completed_at"]) for event in invalidations[snapshot_key])
        check_sufficient = policy["required_restore_check"] == "bytes" or restore["check"] == "bytes_and_app"
        full = fresh and full_current_success(restore, policy["required_restore_check"]) and not invalidated
        project_restore = project_restore or full
        restore_results.append({"restore_id": restore["id"], "scope": restore["scope"], "check": restore["check"],
                                "backup_id": restore["backup_id"], "target_id": record["target_id"],
                                "snapshot_id": record["snapshot_id"], "completed_at": restore["completed_at"],
                                "meets_required_check": check_sufficient,
                                "invalidated_by_later_or_ambiguous_evidence": invalidated,
                                "outcome": restore["outcome"], "fresh": fresh, "matching_member_ids": covered,
                                "satisfies_project_fixture_restore": full})
    if policy["require_project_restore"] and not project_restore:
        block("project_restore_evidence_requirement_unmet", selected)

    candidates = set(document["project"]["candidate_member_ids"])
    return {"schema_version": OUTPUT_VERSION, "synthetic": True, "executable": False,
            "execution_authority": None, "undo_available": False, "source_safe_to_erase": False,
            "revision": document["revision"], "input_digest": digest(document),
            "status": "blocked_review" if blockers else "reviewable_proposal_only",
            "project_id": document["project"]["id"], "member_ids": selected,
            "membership_corrections": {"added": sorted(set(selected) - candidates), "removed": sorted(candidates - set(selected))},
            "proposed_changes": changes, "blockers": blockers,
            "capacity": {"known_logical_copy_bytes": total, "unknown_size_member_ids": unknown_sizes,
                         "reserve_bytes": policy["reserve_bytes"], "required_destination_bytes": required,
                         "observed_free_bytes": destination["free_bytes"], "reclaimed_bytes": 0,
                         "physical_allocation_prediction": None},
            "protection": {"configured_target_ids": sorted(policy["target_ids"]), "members": protection,
                           "restore_observations": restore_results, "restore_alerts": restore_alerts,
                           "required_restore_check": policy["required_restore_check"],
                           "project_restore_satisfied_in_fixture": project_restore,
                           "live_backup_verified": False, "live_restore_verified": False},
            "limitations": ["Synthetic records demonstrate rules, never real backup or restore proof.",
                            "Configuration, provider success, content verification and restore tests are distinct evidence.",
                            "Declared dependency completeness is a reviewed assertion, not application validation.",
                            "A past restore exercise does not prove this proposed new layout opens correctly in its application.",
                            "Failure-domain labels do not prove off-site, ransomware or account isolation.",
                            "No mutation, commands, credentials, provider calls or durable recovery mechanism exist here.",
                            "A future executor must independently revalidate sources, targets, permissions, capacity and approval."]}


def revise(document, *, expected_digest, member_ids, destination_volume_id, destination_folder, acknowledged):
    """User-corrected membership/destination, invalidating the previous review."""
    validate(document)
    if digest(document) != expected_digest:
        raise ContractError("Stale review revision; review the newer decision")
    result = copy.deepcopy(document)
    result["revision"] += 1
    result["decision"] = {"member_ids": list(member_ids), "destination_volume_id": destination_volume_id,
                          "destination_folder": destination_folder, "acknowledged": acknowledged}
    validate(result)
    return result
