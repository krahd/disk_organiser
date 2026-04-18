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
    import model_wrapper  # type: ignore

import importlib
import importlib.util


def _load_model_wrapper():
    try:
        spec = importlib.util.find_spec("model_wrapper")
        if spec is None:
            return None
        return importlib.import_module("model_wrapper")
    except Exception:
        return None


model_wrapper = _load_model_wrapper()
_HAS_EXTERNAL = model_wrapper is not None


class ModelClient:
    """Simple client that delegates to an external model wrapper when available.

    The external model is expected to accept a list of duplicate groups and
    return a list of suggestions of the form:
      [{"keep": <path>, "moves": [{"from": <path>, "to": <path>}, ...]}, ...]
    """

    def __init__(self) -> None:
        self._external = model_wrapper if _HAS_EXTERNAL else None

    def suggest_organise(self, duplicates: List[Dict]) -> List[Dict]:
        """Return organise suggestions for given duplicate groups.

        If an external model wrapper is available, delegate to it. Otherwise
        fall back to a deterministic heuristic that keeps the first file and
        moves others into a `Duplicates` folder beside the kept file.
        """
        if self._external is not None:
            try:
                return self._external.suggest_organise(duplicates)
            except Exception:
                # If external model fails, fall back to heuristic below.
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
