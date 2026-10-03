#!/usr/bin/env python3
"""Disposable end-to-end acceptance for the real Disk Organiser operation API."""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

app_module = importlib.import_module("backend.app")


def _require(response, status: int, label: str) -> dict:
    if response.status_code != status:
        raise RuntimeError(
            f"{label} returned HTTP {response.status_code}: {response.get_data(as_text=True)}"
        )
    payload = response.get_json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} did not return a JSON object")
    return payload


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="disk-organiser-acceptance-") as temp:
        fixture = Path(temp) / "fixture"
        fixture.mkdir()
        first = fixture / "first.txt"
        second = fixture / "second.txt"
        first.write_text("same content\n")
        second.write_text("same content\n")

        client = app_module.app.test_client()

        duplicates = _require(
            client.post("/api/duplicates", json={"paths": [str(fixture)], "min_size": 1}),
            200,
            "duplicate scan",
        )
        if int(duplicates.get("count", 0)) < 1:
            raise RuntimeError("duplicate scan did not find the fixture duplicate")

        suggestions = _require(
            client.post("/api/organise", json={"duplicates": duplicates.get("duplicates", [])}),
            200,
            "organise suggestions",
        ).get("suggestions")
        if not suggestions:
            raise RuntimeError("organise did not produce a reversible suggestion")

        preview = _require(
            client.post("/api/organise/preview", json={"suggestions": suggestions}),
            200,
            "preview",
        )
        op = preview.get("op") or {}
        op_id = op.get("id")
        if not op_id:
            raise RuntimeError("preview did not create an operation id")

        dry_run = _require(
            client.post("/api/organise/execute", json={"op_id": op_id, "dry_run": True}),
            200,
            "dry-run execute",
        )
        if not dry_run.get("actions"):
            raise RuntimeError("dry-run execute did not return actions")
        if not (first.exists() and second.exists()):
            raise RuntimeError("dry-run execute mutated the fixture")

        executed = _require(
            client.post("/api/organise/execute", json={"op_id": op_id}),
            200,
            "execute",
        )
        moved = [item for item in executed.get("executed", []) if item.get("status") == "moved"]
        if not moved:
            raise RuntimeError(f"execute did not move a duplicate: {executed}")
        if first.exists() and second.exists():
            raise RuntimeError("execute reported success but left both duplicates in place")

        undo = _require(
            client.post("/api/organise/undo", json={"op_id": op_id}),
            200,
            "undo",
        )
        if not (first.exists() and second.exists()):
            raise RuntimeError(f"undo did not restore the original fixture: {undo}")
        if first.read_text() != second.read_text():
            raise RuntimeError("restored fixture contents differ")

        print(json.dumps({
            "ok": True,
            "operationId": op_id,
            "duplicates": int(duplicates.get("count", 0)),
            "executedMoves": len(moved),
            "restored": True,
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
