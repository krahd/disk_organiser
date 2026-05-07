"""CI / dev dummy model wrapper.

Provides a simple, deterministic `suggest_organise` implementation used for
local development and CI where no real model is available.
"""

from __future__ import annotations

import os
from typing import Dict, List, Sequence


def suggest_organise(duplicates: List[Dict]) -> List[Dict]:
    """Return safe organise suggestions for given duplicate groups.

    This mirrors the heuristic used elsewhere but places moved files into
    an `AI_Duplicates` folder so outputs are distinguishable in tests.
    """
    suggestions: List[Dict] = []
    for group in duplicates:
        files = group.get("files", [])
        if len(files) <= 1:
            continue
        first = files[0]
        keep = first["path"] if isinstance(first, dict) else first
        moves = []
        for f in files[1:]:
            src = f["path"] if isinstance(f, dict) else f
            dst = os.path.join(
                os.path.dirname(keep), "AI_Duplicates", os.path.basename(src)
            )
            moves.append({"from": src, "to": dst})
        suggestions.append({"keep": keep, "moves": moves, "provider": "ci_dummy"})
    return suggestions


def analyse_drive(
    contexts: Sequence[Dict], preferences: Dict | None = None, history: Sequence[Dict] | None = None
) -> List[Dict]:
    """Return deterministic phase-1/2 actions for tests and local development."""
    del history
    preferences = preferences or {}
    out: List[Dict] = []
    semantic_root_name = preferences.get("semantic_root_name") or "AI_Organised"
    stale_files = [item for item in contexts if item.get("probable_stale_reasons")]
    for item in stale_files[:3]:
        out.append(
            {
                "action_type": "delete_stale",
                "source": item.get("path"),
                "reason": "CI dummy marks stale files for review",
                "confidence": 0.99,
                "group": "Stale files",
                "stale_reasons": list(item.get("probable_stale_reasons") or []),
            }
        )

    by_cluster: Dict[str, List[Dict]] = {}
    for item in contexts:
        key = item.get("near_duplicate_key")
        if key:
            by_cluster.setdefault(key, []).append(item)
    for _key, cluster in by_cluster.items():
        if len(cluster) < 2:
            continue
        root = cluster[0].get("root") or os.path.dirname(cluster[0].get("path") or "")
        group_name = cluster[0].get("extension_group") or "other"
        cluster_signals = sorted({signal for item in cluster for signal in (item.get("near_duplicate_signals") or [])})
        reason = "CI dummy groups similar files into an AI_Organised folder"
        if "matching-content-signature" in cluster_signals:
            reason = "CI dummy groups files with matching sampled content into an AI_Organised folder"
        elif "content-overlap" in cluster_signals:
            reason = "CI dummy groups files with overlapping sampled content into an AI_Organised folder"
        out.append(
            {
                "action_type": "group_files",
                "files": [item.get("path") for item in cluster[:3]],
                "target_dir": os.path.join(root, semantic_root_name, group_name.title()),
                "reason": reason,
                "confidence": 0.83,
                "group": "Semantic groups",
            }
        )
        break
    return out


def refine_actions(
    message: str,
    current_actions: Sequence[Dict],
    contexts: Sequence[Dict],
    preferences: Dict | None = None,
    history: Sequence[Dict] | None = None,
) -> List[Dict]:
    """Deterministically tweak actions so chat flows remain testable."""
    del contexts, preferences, history
    message_lc = (message or "").lower()
    updated = [dict(action) for action in current_actions]
    if "keep downloads" in message_lc:
        updated = [action for action in updated if "/Downloads/" not in str(action.get("destination") or action.get("to") or "")]
    if "delete nothing" in message_lc:
        updated = [action for action in updated if action.get("action_type") != "delete_stale"]
    return updated
