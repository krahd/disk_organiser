"""Synthetic Disk Map contract fixture. No filesystem tree is read or written."""
from __future__ import annotations

import hashlib
import stat
from types import SimpleNamespace

from backend.disk_model import SCHEMA_VERSION, ScanLimits, _entry, compare_inventory, stable_id
from backend.disk_model_analysis import analyse_inventory


def synthetic_model() -> dict:
    root_path = "/synthetic/disk-map-demo"
    root_id = stable_id("root", root_path)
    entries = []
    timestamp = 1767225600 * 10**9
    specs = [
        (".", None), ("Project Aurora", None), ("Project Aurora/pyproject.toml", b"[project]\nname='aurora'\n"),
        ("Project Aurora/design_v1.blend", b"synthetic-version-one"),
        ("Project Aurora/design_v2.blend", b"synthetic-version-two"),
        ("Archive", None), ("Archive/reference.txt", b"synthetic reference notes"),
        ("Inbox", None), ("Inbox/reference-copy.txt", b"synthetic reference notes"),
        ("Inbox/receipt.pdf", b"synthetic illustrative document"),
        ("Cache", None), ("Cache/preview.bin", b"synthetic preview" * 100),
        ("unclassified", None), ("unclassified/unknown.data", b"synthetic unknown format"),
    ]
    for number, (relative, content) in enumerate(specs, 1):
        st = SimpleNamespace(st_dev=1, st_ino=number, st_size=len(content) if content is not None else 0,
                             st_mtime_ns=timestamp, st_ctime_ns=timestamp, st_nlink=1,
                             st_mode=(stat.S_IFDIR | 0o700) if content is None else (stat.S_IFREG | 0o600),
                             st_blocks=8 if content else 0)
        entry = _entry(root_id, relative, st)
        if content is not None:
            entry["hash"] = {"status": "verified", "algorithm": "sha256",
                             "value": hashlib.sha256(content).hexdigest()}
        entries.append(entry)
    # Explicitly illustrative exceptional states, not observations from a user disk.
    unavailable = _entry(root_id, "unclassified/not-readable.data", status="unreadable")
    entries.append(unavailable)
    alias = dict(next(e for e in entries if e["relative_path"] == "Archive/reference.txt"))
    alias.update(id=stable_id("entry", root_id, "Archive/reference-alias.txt"),
                 relative_path="Archive/reference-alias.txt", link_count=2)
    original = next(e for e in entries if e["relative_path"] == "Archive/reference.txt")
    original["link_count"] = 2
    original["fingerprint"]["link_count"] = 2
    entries.append(alias)
    # Some providers do not expose allocation; display unknown rather than zero.
    unknown = next(e for e in entries if e["relative_path"] == "unclassified/unknown.data")
    unknown.update(allocated_bytes=None, allocation_source="unknown")
    entries.sort(key=lambda e: (e["root_id"], e["relative_path"]))
    scan = {"id": stable_id("scan", "synthetic-disk-map-v1"), "started_at": "2026-10-06T12:00:00+00:00",
            "roots": [{"id": root_id, "path": root_path, "status": "observed",
                       "identity": entries[0]["fingerprint"]}], "status": "partial",
            "limits": ScanLimits(hash_files=True).to_dict(), "hash_policy": "bounded_sha256",
            "coverage": {"entries_observed": len(entries),
                         "hashed_files": sum(e["hash"]["status"] == "verified" for e in entries),
                         "hash_status_counts": {"verified": 9}, "hash_attempts": 9,
                         "hashed_bytes": sum(e["logical_bytes"] or 0 for e in entries),
                         "stop_reason": None, "atomic_snapshot": False, "complete_within_policy": False,
                         "status_counts": {"observed": len(entries) - 1, "unreadable": 1}},
            "errors": [{"entry_id": unavailable["id"], "kind": "PermissionError", "errno": 13}],
            "exclusions": [], "uncertainties": ["This is a synthetic demonstration, not a scan of a real disk."]}
    model = {"schema_version": SCHEMA_VERSION, "read_only": True, "synthetic": True,
             "scan": scan, "entries": entries}
    model["changes"] = compare_inventory(None, model)
    model.update(analyse_inventory(model))
    return model
