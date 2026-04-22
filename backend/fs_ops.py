"""Filesystem helpers with dry-run (safe) preview support.

This module provides small utilities to simulate common filesystem
operations (moves, backups, directory creation) without actually
modifying disk. Callers can use these helpers to produce a structured
preview of actions that would be taken when `dry_run=True`.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional


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


def preview_suggestions(
    suggestions: List[dict], op_backup_dir: Optional[str] = None
) -> List[dict]:
    """Return a flat list of planned actions for a given suggestions list."""
    actions: List[dict] = []
    for s in suggestions:
        moves = s.get("moves", [])
        for m in moves:
            src = m.get("from")
            dst = m.get("to")
            actions.append(preview_move_action(src, dst, op_backup_dir))
    return actions


def summarize_actions(actions: List[dict]) -> Dict:
    """Produce a small summary (counts, bytes, dirs) from action list."""
    total_files = 0
    total_bytes = 0
    create_dirs = set()
    missing = []
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
    return {
        "files": total_files,
        "total_bytes": total_bytes,
        "create_dirs": sorted(create_dirs),
        "missing": missing,
    }
