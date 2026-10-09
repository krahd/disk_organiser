"""Display-only projection of one process-local scoped observation.

No route, command, provider, persistence or user-folder selector is connected.
Only the owned-fixture tests exercise this bridge. A saved JSON snapshot is an
unauthenticated historical claim, never a permission or physical-drive identity.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
import re

from backend.observation_session import observe_once

SCHEMA = "disk-organiser/inventory-snapshot/v1"
MAX_BYTES = 1024 * 1024


def _text(value, maximum):
    if (type(value) is not str or not value.strip() or len(value) > maximum
            or re.search(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]", value)):
        raise ValueError("Snapshot text is outside the display contract")
    value.encode("utf-8", "strict")
    return value


def _path(value):
    _text(value, 1024)
    if (value != "." and (value.startswith("/") or "\\" in value
            or any(part in ("", ".", "..") for part in value.split("/")))):
        raise ValueError("Snapshot needs unambiguous relative paths")
    return value


def observe_snapshot(selection, source_label, *, cancel=None, progress=None):
    """Consume a selection once and return a bounded, metadata-only display result.

    ``source_label`` describes the selected folder, not a physical volume. No
    caller-supplied inventory is accepted. Failure/unsupported/cancelled/revoked
    observations have no snapshot. An unrepresentable display projection fails
    closed after retiring the selection, with no partial export.
    """
    _text(source_label, 240)
    result = observe_once(selection, cancel=cancel, progress=progress)
    if result["observation"] is None:
        return {"state": result["state"], "snapshot": None}
    inventory = result["observation"]
    scan = inventory["scan"]
    stamp = _text(scan["started_at"], 40)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", stamp):
        raise ValueError("Snapshot timestamp is outside the display contract")
    if datetime.fromisoformat(stamp.replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("Snapshot timestamp needs a timezone")
    rows = []
    for item in inventory["entries"]:
        size = item["logical_bytes"]
        if size is not None and (type(size) is not int or not 0 <= size < 10**30):
            raise ValueError("Snapshot byte count is outside the display contract")
        rows.append({"path": _path(item["relative_path"]), "kind": item["kind"],
                     "status": item["status"], "logical_bytes": str(size) if size is not None else None})
    reasons = Counter(row["reason"] for row in scan["exclusions"])
    snapshot = {"schema_version": SCHEMA,
                "source": {"label": source_label, "observed_at": stamp,
                           "scan_id": scan["id"], "coverage": scan["status"]},
                "entries": rows,
                "gaps": {"exclusions": [{"reason": _text(reason, 120), "count": str(count)}
                                         for reason, count in sorted(reasons.items())],
                         "error_count": str(len(scan["errors"])),
                         "stop_reason": scan["coverage"]["stop_reason"]}}
    # Component limits bound the projection before serialisation; this final
    # bound controls the transferable artifact, never filesystem scan authority.
    if len(rows) > 2000 or len(reasons) > 32:
        raise ValueError("Snapshot display limits exceeded")
    if len(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) > MAX_BYTES:
        raise ValueError("Snapshot exceeds 1 MiB; no artifact was returned")
    return {"state": result["state"], "snapshot": snapshot}
