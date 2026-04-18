"""Tests for scan-index prune behaviour."""

import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from backend import scan_index  # noqa: E402


def test_prune_by_age(tmp_path, monkeypatch):
    # use a temporary DB file
    db_file = str(tmp_path / "si.db")
    monkeypatch.setattr(scan_index, "DB_FILE", db_file)
    # initialize DB
    scan_index._init_db()

    # create a sample file entry
    p = str(tmp_path / "foo.txt")
    open(p, "wb").write(b"1")
    scan_index.upsert_entry(p, 1, os.path.getmtime(p), sample_hash="s", full_hash=None)

    # set last_seen to very old timestamp
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("UPDATE files SET last_seen = ?", (0,))
    conn.commit()
    conn.close()

    res = scan_index.prune(retention_days=1)
    assert isinstance(res, dict)
    assert res.get("removed_by_age", 0) >= 1 or res.get("total_removed", 0) >= 1
