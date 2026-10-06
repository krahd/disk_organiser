"""Fabricated multi-drive project data; no real files, paths or accounts."""

import copy

from planning_preview import INPUT_VERSION


NOW = "2026-10-06T22:00:00Z"


def sample_document():
    volumes = [
        {"id": "working", "label": "Working SSD", "state": "online", "observed_at": NOW,
         "coverage": "complete", "case_sensitive": False, "unicode_normalization": "NFC",
         "free_bytes": 900_000_000, "failure_domain": "physical-device-working"},
        {"id": "archive", "label": "Archive drive", "state": "online", "observed_at": NOW,
         "coverage": "complete", "case_sensitive": False, "unicode_normalization": "NFC",
         "free_bytes": 900_000_000, "failure_domain": "physical-device-archive"},
        {"id": "shelf", "label": "Offline shelf drive", "state": "offline", "observed_at": "2026-09-01T12:00:00Z",
         "coverage": "unknown", "case_sensitive": None, "unicode_normalization": "unknown",
         "free_bytes": None, "failure_domain": "physical-device-shelf"},
    ]
    entries = []
    for identifier, path, size, dependencies in [
        ("edit", "edit.project", 4000, ["media", "notes"]),
        ("media", "Media/clip.mov", 12_000_000, []),
        ("notes", "Notes/brief.txt", 1000, []),
        ("extra", "Exports/delivery.mov", 500_000, []),
    ]:
        entries.append({"id": identifier, "volume_id": "working", "path": "Projects/Harbour/" + path,
                        "project_path": path, "kind": "file", "bytes": size, "version": "synthetic-v1-" + identifier,
                        "observed_at": NOW, "dependencies": dependencies,
                        "dependency_coverage": "declared_complete", "link_count": 1})
    targets = [
        {"id": "local-backup", "label": "Separate local backup drive", "kind": "local",
         "failure_domain": "physical-device-backup", "region": None},
        {"id": "cloud-backup", "label": "Proposed EU object-storage backup", "kind": "object_storage",
         "failure_domain": "cloud-account-example", "region": "EU example; not connected"},
    ]
    versions = {entry["id"]: entry["version"] for entry in entries if entry["id"] != "extra"}
    backups = [
        {"id": "local-content-evidence", "target_id": "local-backup", "snapshot_id": "synthetic-snapshot-1",
         "observed_at": NOW, "level": "content_verified", "complete": True, "entry_versions": versions},
        {"id": "cloud-config-only", "target_id": "cloud-backup", "snapshot_id": "no-live-snapshot",
         "observed_at": NOW, "level": "declared_configuration", "complete": True, "entry_versions": copy.deepcopy(versions)},
    ]
    return {
        "schema_version": INPUT_VERSION, "synthetic": True, "now": NOW, "revision": 1,
        "volumes": volumes, "entries": entries,
        "project": {"id": "harbour", "label": "Harbour film project", "candidate_member_ids": ["edit", "media", "notes"]},
        "decision": {"member_ids": ["edit", "media", "notes"], "destination_volume_id": "archive",
                     "destination_folder": "Client projects/Harbour", "acknowledged": True},
        "targets": targets,
        "policy": {"target_ids": ["local-backup", "cloud-backup"], "max_evidence_age_hours": 24,
                   "max_restore_age_hours": 168, "max_inventory_age_hours": 2,
                   "required_independent_copies": 1, "require_project_restore": True,
                   "required_restore_check": "bytes_and_app", "reserve_bytes": 64_000_000},
        "backups": backups,
        "restores": [{"id": "local-project-restore", "backup_id": "local-content-evidence", "completed_at": NOW,
                      "scope": "project", "outcome": "passed", "check": "bytes_and_app", "entry_versions": copy.deepcopy(versions)}],
    }


def blocked_example():
    document = sample_document()
    document["entries"][1]["kind"] = "placeholder"
    document["entries"][1]["bytes"] = None
    document["entries"][0]["dependency_coverage"] = "unknown"
    document["backups"][0]["entry_versions"]["notes"] = "synthetic-older-notes"
    document["restores"][0]["scope"] = "sample"
    document["restores"][0]["entry_versions"] = {"edit": "synthetic-v1-edit"}
    return document
