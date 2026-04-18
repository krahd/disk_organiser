"""Model client abstraction.

This module provides a thin wrapper around an external model integration library.
When the external library is unavailable, a safe heuristic fallback is used so
the application remains functional for tests and local usage.
"""
from __future__ import annotations

import os
from typing import List, Dict, TYPE_CHECKING

# Avoid a static `import model_wrapper` which will raise lint/errors in
# environments where the optional integration isn't installed. Use
# importlib to dynamically load the module when present. Keep a
# TYPE_CHECKING import so type-checkers can still resolve the symbol.
if TYPE_CHECKING:  # pragma: no cover - static typing only
    import model_wrapper  # type: ignore  # noqa: F401

import importlib
import importlib.util
import logging
from types import ModuleType


logger = logging.getLogger(__name__)


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
    name = provider_name or os.getenv('MODEL_PROVIDER')
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
        self.provider_name = provider_name or os.getenv('MODEL_PROVIDER')
        self._external = _load_provider(self.provider_name)

    def reload(self, provider_name: str | None = None) -> bool:
        """Reload and switch to a new provider. Returns True if a provider
        module was successfully loaded.
        """
        self.provider_name = provider_name or os.getenv('MODEL_PROVIDER')
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
                fn = getattr(self._external, 'suggest_organise', None)
                if callable(fn):
                    return fn(duplicates)
            except Exception as e:
                logger.debug('External provider failed: %s', e)
                # fall through to heuristic fallback
                pass

        # Heuristic fallback (deterministic and safe)
        suggestions: List[Dict] = []
        for group in duplicates:
            files = group.get('files', [])
            if len(files) <= 1:
                continue
            first = files[0]
            keep = first['path'] if isinstance(first, dict) else first
            moves = []
            for f in files[1:]:
                src = f['path'] if isinstance(f, dict) else f
                dst = os.path.join(os.path.dirname(keep), 'Duplicates', os.path.basename(src))
                moves.append({'from': src, 'to': dst})
            suggestions.append({'keep': keep, 'moves': moves})
        return suggestions
