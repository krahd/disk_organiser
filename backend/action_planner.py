"""Typed action planning and validation for analysis results."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Sequence


def _abs(path: str | None) -> str | None:
    if not path:
        return None
    return os.path.abspath(path)


def _is_within_roots(path: str | None, allowed_roots: Sequence[str]) -> bool:
    candidate = _abs(path)
    if candidate is None:
        return False
    for root in allowed_roots:
        try:
            if os.path.commonpath([candidate, _abs(root)]) == _abs(root):
                return True
        except ValueError:
            continue
    return False


@dataclass
class PlannedAction:
    action_type: str
    source: str | None = None
    destination: str | None = None
    files: List[str] = field(default_factory=list)
    target_dir: str | None = None
    reason: str = ""
    confidence: float = 0.5
    group: str = "General"
    stale_reasons: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        payload = asdict(self)
        payload["action"] = self.action_type
        if self.source:
            payload["from"] = self.source
        if self.destination:
            payload["to"] = self.destination
        return payload


def _coerce_actions(raw_actions: Iterable[Dict]) -> List[Dict]:
    actions: List[Dict] = []
    for action in raw_actions:
        if not isinstance(action, dict):
            continue
        actions.append(action)
    return actions


def _expand_group_action(action: Dict) -> List[Dict]:
    files = action.get("files") or []
    target_dir = action.get("target_dir") or action.get("to")
    out: List[Dict] = []
    for item in files:
        basename = os.path.basename(item)
        out.append(
            {
                "action_type": "move",
                "source": item,
                "destination": os.path.join(target_dir, basename),
                "reason": action.get("reason") or "Grouped by semantic similarity",
                "confidence": action.get("confidence", 0.7),
                "group": action.get("group", "Semantic groups"),
            }
        )
    return out


def _from_legacy_suggestions(suggestions: Sequence[Dict]) -> List[Dict]:
    actions: List[Dict] = []
    for suggestion in suggestions:
        if not isinstance(suggestion, dict):
            continue
        moves = suggestion.get("moves") or []
        for move in moves:
            actions.append(
                {
                    "action_type": "move",
                    "source": move.get("from"),
                    "destination": move.get("to"),
                    "reason": suggestion.get("reason") or "Duplicate consolidation",
                    "confidence": suggestion.get("confidence", 0.95),
                    "group": suggestion.get("group", "Duplicates"),
                    "metadata": {"keep": suggestion.get("keep")},
                }
            )
    return actions


def normalize_actions(items: Sequence[Dict]) -> List[Dict]:
    if not items:
        return []
    looks_legacy = any(isinstance(item, dict) and "moves" in item for item in items)
    if looks_legacy:
        return _from_legacy_suggestions(items)
    normalized: List[Dict] = []
    for action in _coerce_actions(items):
        action_type = (action.get("action_type") or action.get("action") or action.get("type") or "").lower()
        if action_type in {"group_files", "group"}:
            normalized.extend(_expand_group_action(action))
            continue
        normalized.append(
            {
                "action_type": action_type or "move",
                "source": action.get("source") or action.get("from") or action.get("path"),
                "destination": action.get("destination") or action.get("to") or action.get("link"),
                "files": action.get("files") or [],
                "target_dir": action.get("target_dir"),
                "reason": action.get("reason") or "",
                "confidence": float(action.get("confidence", 0.5)),
                "group": action.get("group") or "General",
                "stale_reasons": list(action.get("stale_reasons") or []),
                "metadata": dict(action.get("metadata") or {}),
            }
        )
    return normalized


def validate_actions(
    raw_actions: Sequence[Dict],
    allowed_roots: Sequence[str],
    delete_threshold: float = 0.9,
) -> tuple[List[Dict], List[Dict]]:
    planned: List[Dict] = []
    rejected: List[Dict] = []
    for action in normalize_actions(raw_actions):
        action_type = action.get("action_type")
        source = _abs(action.get("source"))
        destination = _abs(action.get("destination"))
        confidence = float(action.get("confidence") or 0.0)
        group = action.get("group") or "General"

        if action_type in {"move", "reorganise_folder"}:
            if not source or not destination:
                rejected.append({"action": action, "error": "move requires source and destination"})
                continue
            if not _is_within_roots(source, allowed_roots) or not _is_within_roots(destination, allowed_roots):
                rejected.append({"action": action, "error": "move paths must remain within scan roots"})
                continue
        elif action_type == "create_symlink":
            if not source or not destination:
                rejected.append({"action": action, "error": "symlink requires source and destination"})
                continue
            if source == destination:
                rejected.append({"action": action, "error": "symlink cannot point to itself"})
                continue
            if not _is_within_roots(source, allowed_roots) or not _is_within_roots(destination, allowed_roots):
                rejected.append({"action": action, "error": "symlink paths must remain within scan roots"})
                continue
        elif action_type == "delete_stale":
            if not source:
                rejected.append({"action": action, "error": "delete requires source path"})
                continue
            if confidence < delete_threshold:
                rejected.append({"action": action, "error": "delete confidence below threshold"})
                continue
            if not _is_within_roots(source, allowed_roots):
                rejected.append({"action": action, "error": "delete path must remain within scan roots"})
                continue
        else:
            rejected.append({"action": action, "error": f"unsupported action type: {action_type}"})
            continue

        planned_action = PlannedAction(
            action_type=action_type,
            source=source,
            destination=destination,
            files=list(action.get("files") or []),
            target_dir=action.get("target_dir"),
            reason=action.get("reason") or "",
            confidence=confidence,
            group=group,
            stale_reasons=list(action.get("stale_reasons") or []),
            metadata=dict(action.get("metadata") or {}),
        )
        planned.append(planned_action.to_dict())
    return planned, rejected


def group_actions(actions: Sequence[Dict]) -> Dict[str, List[Dict]]:
    groups: Dict[str, List[Dict]] = {}
    for action in normalize_actions(actions):
        groups.setdefault(action.get("group") or "General", []).append(action)
    return groups