"""Filesystem helpers with dry-run (safe) preview support.

This module provides small utilities to simulate common filesystem
operations (moves, backups, directory creation) without actually
modifying disk. Callers can use these helpers to produce a structured
preview of actions that would be taken when `dry_run=True`.
"""

from __future__ import annotations

import os
import shutil
import uuid
import importlib
from pathlib import Path
from typing import Dict, List, Optional

try:
    send2trash_mod = importlib.import_module("send2trash")
    send2trash = getattr(send2trash_mod, "send2trash", None)
except Exception:
    send2trash = None  # type: ignore


def generate_backup_name(backup_dir: str, src_path: str) -> str:
    """Generate a backup path consistent with the op_store naming scheme.

    This mirrors the behaviour in `op_store._relpath_to_backup` without
    importing private symbols.
    """
    name = uuid.uuid4().hex + "_" + os.path.basename(src_path)
    return os.path.join(backup_dir, name)


def _missing_parent_dirs(path: str) -> List[str]:
    """Return list of parent directories that don't currently exist.

    The list is ordered from top-most (closest to root) to lowest.
    """
    out: List[str] = []
    dirpath = os.path.abspath(os.path.dirname(path))
    # climb until an existing path or filesystem root
    stack: List[str] = []
    while dirpath and not os.path.exists(dirpath):
        stack.append(dirpath)
        parent = os.path.dirname(dirpath)
        if parent == dirpath:
            break
        dirpath = parent
    # return in natural creation order (top -> bottom)
    out = list(reversed(stack))
    return out


def preview_move_action(
    src: str, dst: str, op_backup_dir: Optional[str] = None
) -> Dict:
    """Produce a planned action dict for moving `src` to `dst`.

    Only performs safe read-only checks (existence, size) and does not
    modify disk.
    """
    action: Dict = {
        "action": "move",
        "from": src,
        "to": dst,
    }
    if not os.path.exists(src):
        action["status"] = "missing"
        return action

    try:
        size = os.path.getsize(src) if os.path.isfile(src) else None
    except OSError:
        size = None
    action["size"] = size

    dst_abs = os.path.abspath(dst)
    op_backup_dir_abs = os.path.abspath(op_backup_dir) if op_backup_dir else None

    # Use a robust containment check to avoid false positives from simple
    # string-prefix checks (e.g. /data/backup vs /data/backup-other).
    is_in_backup = False
    if op_backup_dir_abs:
        try:
            # Python 3.9+ Path.is_relative_to is reliable
            is_in_backup = Path(dst_abs).resolve().is_relative_to(
                Path(op_backup_dir_abs).resolve()
            )
        except AttributeError:
            # Fallback for older stdlib: use commonpath
            try:
                is_in_backup = os.path.commonpath([dst_abs, op_backup_dir_abs]) == op_backup_dir_abs
            except Exception:
                is_in_backup = dst_abs.startswith(op_backup_dir_abs)
        except Exception:
            is_in_backup = dst_abs.startswith(op_backup_dir_abs)

    if op_backup_dir_abs and is_in_backup:
        # moving into the operation's backup directory (treat as backup)
        action["type"] = "backup_move"
        action["backup"] = dst
        action["create_dirs"] = _missing_parent_dirs(dst)
        action["status"] = "planned"
    else:
        # normal flow: would create a backup then move the file
        action["type"] = "move_with_backup"
        if op_backup_dir_abs:
            action["backup"] = generate_backup_name(op_backup_dir_abs, src)
        else:
            action["backup"] = None
        action["create_dirs"] = _missing_parent_dirs(dst)
        action["status"] = "planned"

    return action


def preview_symlink_action(
    src: str, dst: str, op_backup_dir: Optional[str] = None
) -> Dict:
    action: Dict = {
        "action": "create_symlink",
        "from": src,
        "to": dst,
        "type": "symlink_with_backup",
        "status": "planned",
        "create_dirs": _missing_parent_dirs(dst),
        "backup": generate_backup_name(op_backup_dir, dst) if op_backup_dir and os.path.exists(dst) else None,
    }
    if not src or not os.path.exists(src):
        action["status"] = "missing_source"
    elif os.path.lexists(dst):
        action["status"] = "replace_existing"
    return action


def preview_delete_action(src: str, op_backup_dir: Optional[str] = None) -> Dict:
    action: Dict = {
        "action": "delete_stale",
        "from": src,
        "to": None,
        "type": "delete_with_backup",
        "status": "planned",
    }
    if not os.path.exists(src):
        action["status"] = "missing"
        return action
    try:
        action["size"] = os.path.getsize(src) if os.path.isfile(src) else None
    except OSError:
        action["size"] = None
    action["backup"] = generate_backup_name(op_backup_dir, src) if op_backup_dir else None
    return action


def preview_reorganise_action(
    src: str, dst: str, op_backup_dir: Optional[str] = None
) -> Dict:
    action = preview_move_action(src, dst, op_backup_dir)
    action["action"] = "reorganise_folder"
    action["type"] = "directory_move_with_backup" if os.path.isdir(src) else action.get("type")
    return action


def normalize_actions(actions: List[dict]) -> List[dict]:
    normalized: List[dict] = []
    for item in actions or []:
        if not isinstance(item, dict):
            continue
        if "moves" in item:
            for move in item.get("moves", []):
                normalized.append(
                    {
                        "action": "move",
                        "from": move.get("from"),
                        "to": move.get("to"),
                        "group": item.get("group", "Duplicates"),
                        "reason": item.get("reason", "Duplicate consolidation"),
                        "confidence": item.get("confidence", 0.95),
                    }
                )
            continue
        normalized.append(
            {
                "action": item.get("action") or item.get("action_type") or item.get("type") or "move",
                "from": item.get("from") or item.get("source") or item.get("path"),
                "to": item.get("to") or item.get("destination") or item.get("link"),
                "group": item.get("group", "General"),
                "reason": item.get("reason", ""),
                "confidence": item.get("confidence", 0.5),
                "metadata": item.get("metadata") or {},
                "stale_reasons": item.get("stale_reasons") or [],
            }
        )
    return normalized


def preview_action(action: dict, op_backup_dir: Optional[str] = None) -> dict:
    kind = (action.get("action") or action.get("action_type") or action.get("type") or "move").lower()
    src = action.get("from") or action.get("source") or action.get("path")
    dst = action.get("to") or action.get("destination") or action.get("link")
    if kind == "move":
        planned = preview_move_action(src, dst, op_backup_dir)
    elif kind == "create_symlink":
        planned = preview_symlink_action(src, dst, op_backup_dir)
    elif kind == "delete_stale":
        planned = preview_delete_action(src, op_backup_dir)
    elif kind == "reorganise_folder":
        planned = preview_reorganise_action(src, dst, op_backup_dir)
    else:
        planned = {"action": kind, "from": src, "to": dst, "status": "unsupported"}
    planned["group"] = action.get("group", "General")
    planned["reason"] = action.get("reason", "")
    planned["confidence"] = action.get("confidence", 0.5)
    metadata = action.get("metadata") or {}
    if metadata:
        planned["metadata"] = metadata
    signals = action.get("near_duplicate_signals") or metadata.get("signals") or []
    if signals:
        planned["near_duplicate_signals"] = list(dict.fromkeys(signals))
    if action.get("stale_reasons"):
        planned["stale_reasons"] = list(action.get("stale_reasons") or [])
    return planned


def preview_suggestions(
    suggestions: List[dict], op_backup_dir: Optional[str] = None
) -> List[dict]:
    """Return a flat list of planned actions for a suggestion or action list."""
    return [preview_action(action, op_backup_dir) for action in normalize_actions(suggestions)]


def summarize_actions(actions: List[dict]) -> Dict:
    """Produce a small summary (counts, bytes, dirs) from action list."""
    total_files = 0
    total_bytes = 0
    create_dirs = set()
    missing = []
    grouped = {}
    for a in actions:
        st = a.get("status")
        if st in ("planned", "moved"):
            if a.get("size"):
                try:
                    total_bytes += int(a.get("size") or 0)
                except (TypeError, ValueError):
                    pass
            if st != "missing":
                total_files += 1
        if a.get("create_dirs"):
            for d in a.get("create_dirs"):
                create_dirs.add(d)
        if st == "missing":
            missing.append(a.get("from"))
        group = a.get("group") or "General"
        grouped[group] = grouped.get(group, 0) + 1
    return {
        "actions": len(actions),
        "files": total_files,
        "bytes": total_bytes,
        "total_bytes": total_bytes,
        "create_dirs": sorted(create_dirs),
        "missing": missing,
        "groups": grouped,
    }


def delete_path(path: str) -> None:
    if send2trash:
        send2trash(path)
        return
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.unlink(path)
