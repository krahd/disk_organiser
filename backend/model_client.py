"""Model client abstraction.

This module provides a thin wrapper around an external model integration library.
When the external library is unavailable, a safe heuristic fallback is used so
the application remains functional for tests and local usage.
"""

# pylint: disable=broad-exception-caught


from __future__ import annotations

import importlib
import importlib.util
import logging
import os
from types import ModuleType
from typing import TYPE_CHECKING, Dict, List, Sequence

try:
    from backend.safety import stale_confidence
except Exception:
    from safety import stale_confidence  # type: ignore

# Avoid a static `import model_wrapper` which will raise lint/errors in
# environments where the optional integration isn't installed. Use
# importlib to dynamically load the module when present. Keep a
# TYPE_CHECKING import so type-checkers can still resolve the symbol.
if TYPE_CHECKING:  # pragma: no cover - static typing only
    import model_wrapper  # type: ignore  # noqa: F401


logger = logging.getLogger(__name__)


def _cluster_reason(cluster: Sequence[Dict]) -> str:
    signals = set()
    for item in cluster:
        signals.update(item.get("near_duplicate_signals") or [])
    if "matching-content-signature" in signals:
        return "Files share a strong sampled content signature and appear to be the same or a very close version"
    if "content-overlap" in signals:
        return "Files appear semantically related based on overlapping sampled content and metadata"
    return "Files appear semantically related but are spread across multiple folders"


def _import_by_name(module_name: str) -> ModuleType | None:
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return None
        return importlib.import_module(module_name)
    except Exception as e:
        logger.debug("Failed to import %s: %s", module_name, e)
        return None


def _load_provider(provider_name: str | None = None) -> ModuleType | None:
    """Load a provider module by name.

    Resolution order:
      - If `provider_name` is supplied: try importing it directly.
      - Try `backend.model_wrappers.<provider_name>`.
      - If no provider_name: try top-level `model_wrapper`.
    Returns the module or None.
    """
    name = provider_name or os.getenv("MODEL_PROVIDER")
    if name:
        # try direct import
        mod = _import_by_name(name)
        if mod:
            return mod
        # try backend model_wrappers package
        mod = _import_by_name(f"backend.model_wrappers.{name}")
        if mod:
            return mod
        # try a model_wrappers top-level package
        mod = _import_by_name(f"model_wrappers.{name}")
        if mod:
            return mod
        return None

    # default: try a top-level `model_wrapper` module
    return _import_by_name("model_wrapper")


_HAS_EXTERNAL = _load_provider() is not None


class ModelClient:
    """Simple client that delegates to an external model wrapper when available.

    The external model is expected to accept a list of duplicate groups and
    return a list of suggestions of the form:
      [{"keep": <path>, "moves": [{"from": <path>, "to": <path>}, ...]}, ...]
    """

    def __init__(self, provider_name: str | None = None) -> None:
        """Create a ModelClient and load the initial provider.

        `provider_name` may be a module name (e.g. `ci_dummy`) or None to use
        the default provider resolution (env var or top-level `model_wrapper`).
        """
        self.provider_name = provider_name or os.getenv("MODEL_PROVIDER")
        self._external = _load_provider(self.provider_name)

    def reload(self, provider_name: str | None = None) -> bool:
        """Reload and switch to a new provider. Returns True if a provider
        module was successfully loaded.
        """
        self.provider_name = provider_name or os.getenv("MODEL_PROVIDER")
        self._external = _load_provider(self.provider_name)
        return self._external is not None

    def suggest_organise(self, duplicates: List[Dict]) -> List[Dict]:
        """Return organise suggestions for given duplicate groups.

        If an external model wrapper is available, delegate to it. Otherwise
        fall back to a deterministic heuristic that keeps the first file and
        moves others into a `Duplicates` folder beside the kept file.
        """
        if self._external is not None:
            try:
                fn = getattr(self._external, "suggest_organise", None)
                if callable(fn):
                    return fn(duplicates)
            except Exception as e:
                logger.debug("External provider failed: %s", e)
                # fall through to heuristic fallback

        # Heuristic fallback (deterministic and safe)
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
                    os.path.dirname(keep), "Duplicates", os.path.basename(src)
                )
                moves.append({"from": src, "to": dst})
            suggestions.append({"keep": keep, "moves": moves})
        return suggestions

    def analyse_drive(
        self,
        contexts: Sequence[Dict],
        preferences: Dict | None = None,
        history: Sequence[Dict] | None = None,
    ) -> List[Dict]:
        """Return structured action proposals for a filesystem analysis run."""
        preferences = preferences or {}
        if self._external is not None:
            try:
                fn = getattr(self._external, "analyse_drive", None)
                if callable(fn):
                    return fn(list(contexts), preferences=preferences, history=list(history or []))
            except Exception as e:
                logger.debug("External provider analyse failed: %s", e)

        return self._heuristic_analysis(contexts, preferences, history)

    def refine_actions(
        self,
        message: str,
        current_actions: Sequence[Dict],
        contexts: Sequence[Dict],
        preferences: Dict | None = None,
        history: Sequence[Dict] | None = None,
    ) -> List[Dict]:
        """Return an updated action list after a conversational refinement."""
        preferences = preferences or {}
        if self._external is not None:
            try:
                fn = getattr(self._external, "refine_actions", None)
                if callable(fn):
                    return fn(
                        message,
                        list(current_actions),
                        list(contexts),
                        preferences=preferences,
                        history=list(history or []),
                    )
            except Exception as e:
                logger.debug("External provider refine failed: %s", e)

        message_lc = (message or "").lower()
        actions = [dict(action) for action in current_actions]
        if "delete" in message_lc and "don't" in message_lc:
            actions = [action for action in actions if action.get("action_type") != "delete_stale"]
        if "symlink" in message_lc and ("avoid" in message_lc or "don't" in message_lc):
            actions = [action for action in actions if action.get("action_type") != "create_symlink"]
        if "downloads" in message_lc:
            for action in actions:
                dest = action.get("destination") or action.get("to")
                if action.get("action_type") == "move" and dest:
                    action["destination"] = dest.replace("/Organised/", "/Downloads/Organised/")
                    action["to"] = action["destination"]
        return actions or self._heuristic_analysis(contexts, preferences, history)

    def _heuristic_analysis(
        self,
        contexts: Sequence[Dict],
        preferences: Dict | None = None,
        history: Sequence[Dict] | None = None,
    ) -> List[Dict]:
        del history
        preferences = preferences or {}
        semantic_root_name = preferences.get("semantic_root_name") or "Organised"
        actions: List[Dict] = []

        by_cluster: Dict[str, List[Dict]] = {}
        by_normalized_name: Dict[str, List[Dict]] = {}
        for item in contexts:
            key = item.get("near_duplicate_key")
            if key:
                by_cluster.setdefault(key, []).append(item)
            normalized = item.get("normalized_name")
            if normalized:
                by_normalized_name.setdefault(normalized, []).append(item)

        seen_sources = set()

        for item in contexts:
            stale_reasons = list(item.get("probable_stale_reasons") or [])
            if not stale_reasons:
                continue
            source = item.get("path")
            if source in seen_sources:
                continue
            confidence = stale_confidence(stale_reasons)
            if confidence < 0.9:
                continue
            seen_sources.add(source)
            actions.append(
                {
                    "action_type": "delete_stale",
                    "source": source,
                    "reason": f"Likely stale file: {', '.join(stale_reasons)}",
                    "confidence": confidence,
                    "group": "Stale files",
                    "stale_reasons": stale_reasons,
                }
            )

        for key, cluster in by_cluster.items():
            if len(cluster) < 2:
                continue
            cluster = sorted(cluster, key=lambda item: (item.get("depth", 0), item.get("age_days", 0)))
            roots = {item.get("parent") for item in cluster}
            if len(roots) < 2:
                continue
            extension_group = cluster[0].get("extension_group") or "other"
            semantic_dir = os.path.join(cluster[0].get("root") or os.path.dirname(cluster[0].get("path") or ""), semantic_root_name, extension_group.title())
            move_candidates = [item.get("path") for item in cluster if semantic_root_name.lower() not in (item.get("path") or "").lower()]
            if len(move_candidates) >= 2:
                actions.append(
                    {
                        "action_type": "group_files",
                        "files": move_candidates[:6],
                        "target_dir": semantic_dir,
                        "reason": _cluster_reason(cluster),
                        "confidence": 0.72,
                        "group": "Semantic groups",
                        "metadata": {"cluster": key, "signals": sorted({signal for item in cluster for signal in (item.get("near_duplicate_signals") or [])})},
                    }
                )

        for normalized_name, items in by_normalized_name.items():
            if len(items) != 2:
                continue
            a, b = items
            if a.get("size") != b.get("size"):
                continue
            if a.get("path") in seen_sources or b.get("path") in seen_sources:
                continue
            if not a.get("content_signature") or a.get("content_signature") != b.get("content_signature"):
                continue
            downloads_candidate = None
            canonical_candidate = None
            for item in items:
                path_lc = (item.get("path") or "").lower()
                if "/downloads/" in path_lc or "/desktop/" in path_lc:
                    downloads_candidate = item
                else:
                    canonical_candidate = item
            if downloads_candidate and canonical_candidate:
                seen_sources.add(downloads_candidate.get("path"))
                actions.append(
                    {
                        "action_type": "create_symlink",
                        "source": canonical_candidate.get("path"),
                        "destination": downloads_candidate.get("path"),
                        "reason": "Keep a canonical copy and replace the secondary copy with a symlink because sampled content matches",
                        "confidence": 0.7,
                        "group": "Symlinks",
                    }
                )

        return actions
