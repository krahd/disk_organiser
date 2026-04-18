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

import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def _heuristic(duplicates: List[Dict], suffix: str = 'Modelito_Duplicates') -> List[Dict]:
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
            dst = os.path.join(os.path.dirname(keep), suffix, os.path.basename(src))
            moves.append({'from': src, 'to': dst})
        suggestions.append({'keep': keep, 'moves': moves, 'provider': 'modelito_fallback'})
    return suggestions


def suggest_organise(duplicates: List[Dict]) -> List[Dict]:
    """Return organise suggestions using Modelito when available.

    This implementation will attempt to call a configured HTTP endpoint
    (`MODELITO_URL`). If the endpoint or `requests` is unavailable the
    function returns a deterministic heuristic so callers don't fail.
    """
    # simulation mode (useful for CI / local testing)
    if os.getenv('MODELITO_SIMULATE') == '1':
        return _heuristic(duplicates, suffix='Modelito_Sim')

    url = os.getenv('MODELITO_URL')
    if not url:
        # no external endpoint configured: deterministic fallback
        return _heuristic(duplicates)

    try:
        import requests  # type: ignore
    except Exception:
        logger.debug('requests not available; falling back to heuristic')
        return _heuristic(duplicates)

    try:
        headers = {'Content-Type': 'application/json'}
        api_key = os.getenv('MODELITO_API_KEY')
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        payload = {'duplicates': duplicates}
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if not resp.ok:
            logger.debug('Modelito endpoint returned error: %s', resp.status_code)
            return _heuristic(duplicates)
        data = resp.json()
        # Expect provider to return {'suggestions': [...] } or a bare list
        if isinstance(data, dict) and 'suggestions' in data:
            return data['suggestions']
        if isinstance(data, list):
            return data
        logger.debug('Unexpected Modelito response shape; falling back')
        return _heuristic(duplicates)
    except Exception as e:
        logger.debug('Modelito call failed: %s', e)
        return _heuristic(duplicates)
