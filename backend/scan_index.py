"""Persistent scan index to cache sample and full hashes.

Stores per-path metadata in a small SQLite DB to avoid re-hashing unchanged
files across scans. Intended to be used by `backend.utils.find_duplicates`.
"""

# pylint: disable=broad-exception-caught,too-many-nested-blocks,duplicate-code

import hashlib
import os
import sqlite3
import time
from typing import List, Optional

BASE = os.path.dirname(__file__)
DB_FILE = os.path.join(BASE, "scan_index.db")
INDEX_PRAGMA = "PRAGMA journal_mode=WAL"


def _connect(db: Optional[str] = None):
    path = db or DB_FILE
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    try:
        conn.execute(INDEX_PRAGMA)
        conn.execute("PRAGMA foreign_keys=ON")
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
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_size_sample ON files(size, sample_hash)"
    )
    conn.commit()
    conn.close()


_init_db()


def get_entry(path: str) -> Optional[dict]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT path, size, mtime, sample_hash, full_hash, last_seen "
        "FROM files WHERE path=?",
        (path,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "path": row[0],
        "size": row[1],
        "mtime": row[2],
        "sample_hash": row[3],
        "full_hash": row[4],
        "last_seen": row[5],
    }


def upsert_entry(
    path: str,
    size: int,
    mtime: float,
    sample_hash: Optional[str] = None,
    full_hash: Optional[str] = None,
):
    conn = _connect()
    cur = conn.cursor()
    now = time.time()
    sql = (
        "INSERT OR REPLACE INTO files (path, size, mtime, sample_hash, full_hash, "
        "last_seen) VALUES (?, ?, ?, ?, ?, ?)"
    )
    cur.execute(sql, (path, size, mtime, sample_hash, full_hash, now))
    conn.commit()
    conn.close()


def set_full_hash(path: str, full_hash: str):
    conn = _connect()
    cur = conn.cursor()
    now = time.time()
    cur.execute(
        "UPDATE files SET full_hash=?, last_seen=? WHERE path=?",
        (full_hash, now, path),
    )
    conn.commit()
    conn.close()


def find_paths_by_size_and_sample(size: int, sample_hash: str) -> List[str]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT path FROM files WHERE size=? AND sample_hash=?", (size, sample_hash)
    )
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def cleanup_missing():
    """Remove entries whose path no longer exists on disk."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT path FROM files")
    rows = cur.fetchall()
    removed = 0
    for (p,) in rows:
        if not os.path.exists(p):
            cur.execute("DELETE FROM files WHERE path=?", (p,))
            removed += 1
    conn.commit()
    conn.close()
    return removed


def prune(
    retention_days: int | None = None,
    max_entries: int | None = None,
    dry_run: bool = False,
):
    """Prune index entries by age (last_seen) and/or reduce total entries.

    Returns a summary dict with counts of removed rows.
    """
    conn = _connect()
    cur = conn.cursor()
    removed_by_age = 0
    removed_by_max = 0
    try:
        now = time.time()
        if retention_days is not None:
            threshold = now - float(retention_days) * 86400.0
            # count entries to remove
            cur.execute(
                "SELECT COUNT(*) FROM files WHERE last_seen IS NOT NULL "
                "AND last_seen < ?",
                (threshold,),
            )
            removed_by_age = cur.fetchone()[0]
            if not dry_run:
                cur.execute(
                    "DELETE FROM files WHERE last_seen IS NOT NULL "
                    "AND last_seen < ?",
                    (threshold,),
                )

        if max_entries is not None:
            cur.execute("SELECT COUNT(*) FROM files")
            total = cur.fetchone()[0]
            if total > int(max_entries):
                to_remove = total - int(max_entries)
                cur.execute(
                    "SELECT path FROM files ORDER BY last_seen ASC NULLS FIRST "
                    "LIMIT ?",
                    (to_remove,),
                )
                rows = cur.fetchall()
                paths = [r[0] for r in rows]
                if not dry_run:
                    for p in paths:
                        cur.execute("DELETE FROM files WHERE path=?", (p,))
                removed_by_max = len(paths)

        conn.commit()
    finally:
        conn.close()
    return {
        "removed_by_age": removed_by_age,
        "removed_by_max": removed_by_max,
        "total_removed": removed_by_age + removed_by_max,
    }


def stats():
    """Return basic statistics about the index."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM files")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM files WHERE full_hash IS NOT NULL")
    full = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM files WHERE sample_hash IS NOT NULL")
    sample = cur.fetchone()[0]
    conn.close()
    return {"total": total, "with_full": full, "with_sample": sample}


def _local_sample_hash(path: str, sample_size: int = 4096) -> str:
    size = os.path.getsize(path)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        if size <= sample_size * 2:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
            return h.hexdigest()
        first = f.read(sample_size)
        h.update(first)
        try:
            f.seek(-sample_size, os.SEEK_END)
            last = f.read(sample_size)
            h.update(last)
        except OSError:
            f.seek(0)
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    return h.hexdigest()


def rebuild_index(
    paths: list, min_size: int = 1, sample_size: int = 4096, progress_callback=None
):
    """Walk provided paths and (re)populate sample_hash entries in the index.

    This operation is synchronous and may take time on large trees.
    Returns a summary dict with counts and any errors encountered.
    """
    scanned = 0
    upserted = 0
    errors = []
    for root in paths:
        if not os.path.exists(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                try:
                    st = os.stat(fp)
                    if st.st_size < min_size:
                        continue
                    sh = _local_sample_hash(fp, sample_size=sample_size)
                    try:
                        upsert_entry(
                            fp,
                            st.st_size,
                            os.path.getmtime(fp),
                            sample_hash=sh,
                            full_hash=None,
                        )
                        upserted += 1
                    except Exception as e:
                        errors.append(str(e))
                    scanned += 1
                    if progress_callback and scanned % 25 == 0:
                        try:
                            progress_callback(
                                {
                                    "status": "rebuilding",
                                    "processed": scanned,
                                    "upserted": upserted,
                                }
                            )
                        except Exception:
                            pass
                except (OSError, PermissionError) as e:
                    errors.append(str(e))
                    continue
    # final progress update
    if progress_callback:
        try:
            progress_callback(
                {"status": "finished", "processed": scanned, "upserted": upserted}
            )
        except Exception:
            pass
    return {"scanned": scanned, "upserted": upserted, "errors": errors}
