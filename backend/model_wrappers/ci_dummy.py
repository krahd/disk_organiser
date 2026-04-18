"""CI / dev dummy model wrapper.

Provides a simple, deterministic `suggest_organise` implementation used for
local development and CI where no real model is available.
"""
from __future__ import annotations

import os
from typing import List, Dict


def suggest_organise(duplicates: List[Dict]) -> List[Dict]:
    """Return safe organise suggestions for given duplicate groups.

    This mirrors the heuristic used elsewhere but places moved files into
    an `AI_Duplicates` folder so outputs are distinguishable in tests.
    """
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
            dst = os.path.join(os.path.dirname(keep), 'AI_Duplicates', os.path.basename(src))
            moves.append({'from': src, 'to': dst})
        suggestions.append({'keep': keep, 'moves': moves, 'provider': 'ci_dummy'})
    return suggestions
