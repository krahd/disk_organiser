"""Persistent scan index to cache sample and full hashes.

Stores per-path metadata in a small SQLite DB to avoid re-hashing unchanged
files across scans. Intended to be used by `backend.utils.find_duplicates`.
"""

import os
import json
import sqlite3
import time
from typing import Optional, List

BASE = os.path.dirname(__file__)
DB_FILE = os.path.join(BASE, 'scan_index.db')
INDEX_PRAGMA = 'PRAGMA journal_mode=WAL'


def _connect(db: Optional[str] = None):
    path = db or DB_FILE
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    try:
        conn.execute(INDEX_PRAGMA)
        conn.execute('PRAGMA foreign_keys=ON')
    except Exception:
        pass
    return conn


def _init_db(db: Optional[str] = None):
    conn = _connect(db)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            size INTEGER,
            mtime REAL,
            sample_hash TEXT,
            full_hash TEXT,
            last_seen REAL
        )
        """
    )
    cur.execute('CREATE INDEX IF NOT EXISTS idx_size_sample ON files(size, sample_hash)')
    conn.commit()
    conn.close()


_init_db()


def get_entry(path: str) -> Optional[dict]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute('SELECT path,size,mtime,sample_hash,full_hash,last_seen FROM files WHERE path=?', (path,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'path': row[0],
        'size': row[1],
        'mtime': row[2],
        'sample_hash': row[3],
        'full_hash': row[4],
        'last_seen': row[5],
    }


def upsert_entry(path: str, size: int, mtime: float, sample_hash: Optional[str] = None, full_hash: Optional[str] = None):
    conn = _connect()
    cur = conn.cursor()
    now = time.time()
    cur.execute('INSERT OR REPLACE INTO files (path,size,mtime,sample_hash,full_hash,last_seen) VALUES (?, ?, ?, ?, ?, ?)',
                (path, size, mtime, sample_hash, full_hash, now))
    conn.commit()
    conn.close()


def set_full_hash(path: str, full_hash: str):
    conn = _connect()
    cur = conn.cursor()
    now = time.time()
    cur.execute('UPDATE files SET full_hash=?, last_seen=? WHERE path=?', (full_hash, now, path))
    conn.commit()
    conn.close()


def find_paths_by_size_and_sample(size: int, sample_hash: str) -> List[str]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute('SELECT path FROM files WHERE size=? AND sample_hash=?', (size, sample_hash))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def cleanup_missing():
    """Remove entries whose path no longer exists on disk."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute('SELECT path FROM files')
    rows = cur.fetchall()
    removed = 0
    for (p,) in rows:
        if not os.path.exists(p):
            cur.execute('DELETE FROM files WHERE path=?', (p,))
            removed += 1
    conn.commit()
    conn.close()
    return removed
