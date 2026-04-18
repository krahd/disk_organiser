"""Tests for scan-index admin utilities and endpoints."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from backend import scan_index  # noqa: E402


def test_scan_index_stats_returns_counts():
    s = scan_index.stats()
    assert isinstance(s, dict)
    assert 'total' in s and isinstance(s['total'], int)
    assert 'with_full' in s and isinstance(s['with_full'], int)
    assert 'with_sample' in s and isinstance(s['with_sample'], int)
