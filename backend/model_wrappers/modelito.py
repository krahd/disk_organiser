"""Modelito provider wrapper.

This module provides a thin adapter for a Modelito-based provider. It is
intentionally defensive: if an external HTTP/SDK integration is unavailable
the wrapper falls back to a safe deterministic heuristic so the application
remains functional for local development and tests.

Configuration (environment):
- MODELITO_URL: optional HTTP endpoint to call for suggestions
- MODELITO_API_KEY: optional API key passed as Authorization header
- MODELITO_SIMULATE=1: if set, return deterministic simulated suggestions
"""

from __future__ import annotations

import importlib
import json
import logging
import os
from typing import Any, Dict, List, Sequence, cast

logger = logging.getLogger(__name__)


def _reject_delete_intent(message_lc: str) -> bool:
    patterns = (
        "don't delete",
        "do not delete",
        "delete nothing",
        "delete nothing from",
        "no delete",
        "keep everything",
        "keep all",
    )
    return any(pattern in message_lc for pattern in patterns)


def _load_sdk():
    try:
        return importlib.import_module("modelito")
    except Exception as exc:
        logger.debug("Modelito SDK unavailable: %s", exc)
        return None


def _configured_provider(preferences: Dict | None = None) -> str:
    prefs = preferences or {}
    provider = prefs.get("modelito_provider") or os.getenv("MODELITO_PROVIDER") or "ollama"
    return str(provider).strip() or "ollama"


def _configured_model(preferences: Dict | None = None) -> str | None:
    prefs = preferences or {}
    for key in ("ollama_model", "modelito_model"):
        value = prefs.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for env_name in ("MODELITO_MODEL", "OLLAMA_MODEL"):
        value = os.getenv(env_name)
        if value:
            return value.strip()
    return None


def _extract_json_payload(text: str) -> Any:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        parts = stripped.split("```")
        if len(parts) >= 3:
            stripped = parts[1]
            if stripped.lstrip().startswith("json"):
                stripped = stripped.lstrip()[4:]
    for opener, closer in (("[", "]"), ("{", "}")):
        start = stripped.find(opener)
        end = stripped.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidate = stripped[start: end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    raise ValueError("No JSON payload found in Modelito response")


def _coerce_action_list(payload: Any) -> List[Dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("actions", "suggestions"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise ValueError("Modelito response did not contain an action list")


def _compact_contexts(contexts: Sequence[Dict], limit: int = 60) -> List[Dict]:
    compact: List[Dict] = []
    for item in list(contexts)[:limit]:
        compact.append(
            {
                "path": item.get("path"),
                "root": item.get("root"),
                "parent": item.get("parent"),
                "name": item.get("name"),
                "extension_group": item.get("extension_group"),
                "size": item.get("size"),
                "age_days": item.get("age_days"),
                "near_duplicate_key": item.get("near_duplicate_key"),
                "near_duplicate_signals": item.get("near_duplicate_signals"),
                "probable_stale_reasons": item.get("probable_stale_reasons"),
            }
        )
    return compact


def _simulate_analysis(contexts: Sequence[Dict], preferences: Dict | None = None) -> List[Dict]:
    preferences = preferences or {}
    semantic_root_name = preferences.get("semantic_root_name") or "Organised"
    actions: List[Dict] = []
    for item in contexts:
        source = item.get("path")
        root = item.get("root") or os.path.dirname(source or "")
        if not source or semantic_root_name.lower() in source.lower():
            continue
        extension_group = item.get("extension_group") or "Other"
        destination = os.path.join(root, semantic_root_name, str(
            extension_group).title(), os.path.basename(source))
        actions.append(
            {
                "action_type": "move",
                "source": source,
                "destination": destination,
                "reason": "Modelito simulation grouped the file by type for review",
                "confidence": 0.6,
                "group": "Semantic groups",
            }
        )
    return actions[:25]


def _simulate_refine(message: str, current_actions: Sequence[Dict]) -> List[Dict]:
    message_lc = (message or "").lower()
    actions = [dict(action) for action in current_actions]
    if "delete" in message_lc and _reject_delete_intent(message_lc):
        actions = [action for action in actions if action.get("action_type") != "delete_stale"]
    return actions


def _call_modelito_json(prompt: str, preferences: Dict | None = None) -> List[Dict]:
    sdk = cast(Any, _load_sdk())
    if sdk is None:
        raise RuntimeError("Modelito SDK is unavailable")
    client = sdk.Client(provider=_configured_provider(
        preferences), model=_configured_model(preferences))
    messages = [
        sdk.Message(
            role="system",
            content=(
                "You plan safe filesystem organisation actions. "
                "Return JSON only with an array of action objects. "
                "Use only these action_type values: move, delete_stale, create_symlink, reorganise_folder. "
                "Each action should include source and destination when applicable, plus reason, confidence, and group."
            ),
        ),
        sdk.Message(role="user", content=prompt),
    ]
    response = client.summarize(messages)
    return _coerce_action_list(_extract_json_payload(response))


def _heuristic(
    duplicates: List[Dict], suffix: str = "Modelito_Duplicates"
) -> List[Dict]:
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
            dst = os.path.join(os.path.dirname(keep), suffix, os.path.basename(src))
            moves.append({"from": src, "to": dst})
        suggestions.append(
            {"keep": keep, "moves": moves, "provider": "modelito_fallback"}
        )
    return suggestions


def suggest_organise(duplicates: List[Dict]) -> List[Dict]:
    """Return organise suggestions using Modelito when available.

    This implementation will attempt to call a configured HTTP endpoint
    (`MODELITO_URL`). If the endpoint or `requests` is unavailable the
    function returns a deterministic heuristic so callers don't fail.
    """
    # simulation mode (useful for CI / local testing)
    if os.getenv("MODELITO_SIMULATE") == "1":
        return _heuristic(duplicates, suffix="Modelito_Sim")

    prompt = (
        "Review duplicate file groups and return JSON suggestions for which file to keep and which files to move. "
        "Return an array of objects with keys keep, moves, provider. Each moves item must contain from and to.\n"
        f"duplicate_groups={json.dumps(duplicates[:25])}"
    )
    try:
        suggestions = _call_modelito_json(prompt)
        if suggestions:
            for item in suggestions:
                item.setdefault("provider", "modelito")
            return suggestions
    except Exception as exc:
        logger.debug("Modelito SDK duplicate planning failed: %s", exc)

    url = os.getenv("MODELITO_URL")
    if not url:
        # no external endpoint configured: deterministic fallback
        return _heuristic(duplicates)

    try:
        requests = cast(Any, importlib.import_module("requests"))
    except Exception:
        logger.debug("requests not available; falling back to heuristic")
        return _heuristic(duplicates)

    try:
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("MODELITO_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {"duplicates": duplicates}
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if not resp.ok:
            logger.debug("Modelito endpoint returned error: %s", resp.status_code)
            return _heuristic(duplicates)
        data = resp.json()
        # Expect provider to return {'suggestions': [...] } or a bare list
        if isinstance(data, dict) and "suggestions" in data:
            return data["suggestions"]
        if isinstance(data, list):
            return data
        logger.debug("Unexpected Modelito response shape; falling back")
        return _heuristic(duplicates)
    except Exception as e:
        logger.debug("Modelito call failed: %s", e)
        return _heuristic(duplicates)


def analyse_drive(
    contexts: Sequence[Dict],
    preferences: Dict | None = None,
    history: Sequence[Dict] | None = None,
) -> List[Dict]:
    """Return filesystem actions planned through the Modelito SDK."""
    del history
    if os.getenv("MODELITO_SIMULATE") == "1":
        return _simulate_analysis(contexts, preferences)
    prompt = (
        "Plan safe filesystem organisation actions for the supplied file contexts. "
        "Prefer reversible moves and only suggest delete_stale when the stale reasons are strong. "
        f"preferences={json.dumps(preferences or {})}\n"
        f"contexts={json.dumps(_compact_contexts(contexts))}"
    )
    actions = _call_modelito_json(prompt, preferences)
    if not actions:
        raise RuntimeError("Modelito returned no actions")
    return actions


def refine_actions(
    message: str,
    current_actions: Sequence[Dict],
    contexts: Sequence[Dict],
    preferences: Dict | None = None,
    history: Sequence[Dict] | None = None,
) -> List[Dict]:
    """Refine action proposals through the Modelito SDK."""
    if os.getenv("MODELITO_SIMULATE") == "1":
        return _simulate_refine(message, current_actions)
    prompt = (
        "Refine the current filesystem action plan based on the user's message. "
        "Keep only valid actions that use paths from the supplied contexts. "
        f"preferences={json.dumps(preferences or {})}\n"
        f"history={json.dumps(list(history or []))}\n"
        f"message={json.dumps(message)}\n"
        f"current_actions={json.dumps(list(current_actions))}\n"
        f"contexts={json.dumps(_compact_contexts(contexts))}"
    )
    actions = _call_modelito_json(prompt, preferences)
    if not actions:
        raise RuntimeError("Modelito returned no refined actions")
    return actions
