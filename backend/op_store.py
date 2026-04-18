"""SQLite-backed operation store for preview/execute/undo lifecycle.

Implements a small transactional store to replace the previous JSON file
approach. Keeps file-based backups under `ops_backups/` for each operation.
"""

import json
import os
import time
import uuid
import shutil
import sqlite3
from typing import Optional

BASE = os.path.dirname(__file__)
DB_FILE = os.path.join(BASE, 'ops.db')
BACKUP_ROOT = os.path.join(BASE, 'ops_backups')
INDEX_PRAGMA = 'PRAGMA journal_mode=WAL'


def _ensure_dirs():
    os.makedirs(BACKUP_ROOT, exist_ok=True)


def _connect(db: Optional[str] = None):
    path = db or DB_FILE
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    try:
        conn.execute(INDEX_PRAGMA)
        conn.execute('PRAGMA foreign_keys=ON')
    except Exception:
        # best-effort: continue without explicit pragmas if unsupported
        pass
    return conn


def _init_db(db: Optional[str] = None):
    conn = _connect(db)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ops (
            id TEXT PRIMARY KEY,
            suggestions TEXT,
            metadata TEXT,
            status TEXT,
            created_at REAL,
            backup_dir TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS executed_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            op_id TEXT,
            seq INTEGER,
            action TEXT,
            FOREIGN KEY(op_id) REFERENCES ops(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()


# initialize DB on import if not present
_init_db()


def _row_to_op(row: sqlite3.Row) -> dict:
    return {
        'id': row[0],
        'suggestions': json.loads(row[1]) if row[1] else [],
        'metadata': json.loads(row[2]) if row[2] else {},
        'status': row[3],
        'created_at': row[4],
        'backup_dir': row[5],
    }


def create_op(suggestions: list, metadata: dict | None = None, op_id: str | None = None) -> dict:
    _ensure_dirs()
    _init_db()
    if not op_id:
        op_id = uuid.uuid4().hex
    backup_dir = os.path.join(BACKUP_ROOT, op_id)
    os.makedirs(backup_dir, exist_ok=True)
    created_at = time.time()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO ops (id, suggestions, metadata, status, created_at, backup_dir) VALUES (?, ?, ?, ?, ?, ?)",
        (op_id, json.dumps(suggestions), json.dumps(metadata or {}), 'preview', created_at, backup_dir),
    )
    conn.commit()
    conn.close()
    return {
        'id': op_id,
        'suggestions': suggestions,
        'metadata': metadata or {},
        'status': 'preview',
        'created_at': created_at,
        'backup_dir': backup_dir,
        'executed_actions': [],
    }


def get_op(op_id: str) -> dict | None:
    _init_db()
    conn = _connect()
    cur = conn.cursor()
    cur.execute('SELECT id,suggestions,metadata,status,created_at,backup_dir FROM ops WHERE id=?', (op_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    op = _row_to_op(row)
    # load executed actions
    cur.execute('SELECT seq, action FROM executed_actions WHERE op_id=? ORDER BY seq ASC', (op_id,))
    acts = []
    for seq, action in cur.fetchall():
        try:
            acts.append(json.loads(action))
        except Exception:
            acts.append({'raw': action})
    op['executed_actions'] = acts
    conn.close()
    return op


def update_op(op_id: str, **kwargs) -> dict | None:
    _init_db()
    # only allow updating certain columns
    allowed = {'suggestions', 'metadata', 'status', 'backup_dir'}
    sets = []
    vals = []
    for k, v in kwargs.items():
        if k in allowed:
            if isinstance(v, (dict, list)):
                v = json.dumps(v)
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        return get_op(op_id)
    vals.append(op_id)
    conn = _connect()
    cur = conn.cursor()
    cur.execute(f"UPDATE ops SET {', '.join(sets)} WHERE id=?", tuple(vals))
    conn.commit()
    conn.close()
    return get_op(op_id)


def list_ops() -> dict:
    _init_db()
    conn = _connect()
    cur = conn.cursor()
    cur.execute('SELECT id,suggestions,metadata,status,created_at,backup_dir FROM ops')
    rows = cur.fetchall()
    out = {}
    for row in rows:
        op = _row_to_op(row)
        out[op['id']] = op
    conn.close()
    return out


def list_backups() -> dict:
    ops = list_ops()
    out = {}
    for opid, op in ops.items():
        files = []
        bdir = op.get('backup_dir')
        if bdir and os.path.exists(bdir):
            for root, _, fns in os.walk(bdir):
                for fn in fns:
                    fp = os.path.join(root, fn)
                    try:
                        files.append({
                            'path': fp,
                            'size': os.path.getsize(fp),
                            'mtime': os.path.getmtime(fp),
                        })
                    except (OSError, PermissionError):
                        continue
        out[opid] = {
            'metadata': op.get('metadata', {}),
            'files': files,
            'status': op.get('status', ''),
        }
    return out


def set_op_status(op_id: str, status: str):
    return update_op(op_id, status=status) is not None


def add_executed_action(op_id: str, action: dict):
    _init_db()
    conn = _connect()
    cur = conn.cursor()
    # determine next seq
    cur.execute('SELECT MAX(seq) FROM executed_actions WHERE op_id=?', (op_id,))
    row = cur.fetchone()
    seq = (row[0] or 0) + 1
    cur.execute('INSERT INTO executed_actions (op_id, seq, action) VALUES (?, ?, ?)',
                (op_id, seq, json.dumps(action)))
    conn.commit()
    conn.close()
    return True


def _relpath_to_backup(backup_dir: str, src_path: str) -> str:
    name = uuid.uuid4().hex + '_' + os.path.basename(src_path)
    return os.path.join(backup_dir, name)


def backup_file(op_id: str, src_path: str) -> str | None:
    op = get_op(op_id)
    if not op:
        return None
    backup_dir = op['backup_dir']
    os.makedirs(backup_dir, exist_ok=True)
    target = _relpath_to_backup(backup_dir, src_path)
    try:
        shutil.copy2(src_path, target)
        return target
    except (OSError, shutil.Error):
        return None


def undo_op(op_id: str) -> dict:
    op = get_op(op_id)
    if not op:
        return {'error': 'not found'}
    # load executed actions ordered descending
    conn = _connect()
    cur = conn.cursor()
    cur.execute('SELECT action FROM executed_actions WHERE op_id=? ORDER BY seq DESC', (op_id,))
    rows = cur.fetchall()
    results = []
    for (action_json,) in rows:
        try:
            a = json.loads(action_json)
        except Exception:
            results.append({'error': 'invalid action', 'raw': action_json})
            continue
        backup = a.get('backup')
        orig = a.get('from')
        try:
            if backup and os.path.exists(backup):
                os.makedirs(os.path.dirname(orig), exist_ok=True)
                shutil.move(backup, orig)
                results.append({'restored': orig})
            else:
                results.append({'failed': orig})
        except (OSError, shutil.Error) as e:
            results.append({'error': str(e), 'file': orig})
    conn.close()
    set_op_status(op_id, 'reverted')
    return {'restored': results}


def cleanup_recycle(retention_days: int = 30) -> dict:
    now = time.time()
    cutoff = now - (retention_days * 24 * 3600)
    removed = 0
    scanned = 0
    if not os.path.exists(BACKUP_ROOT):
        return {'scanned': 0, 'removed': 0}
    for opid in os.listdir(BACKUP_ROOT):
        opdir = os.path.join(BACKUP_ROOT, opid)
        if not os.path.isdir(opdir):
            continue
        for root, _, files in os.walk(opdir):
            for fn in files:
                fp = os.path.join(root, fn)
                try:
                    scanned += 1
                    if os.path.getmtime(fp) < cutoff:
                        os.remove(fp)
                        removed += 1
                except (OSError, PermissionError):
                    continue
        # attempt to remove empty dirs
        try:
            for root, _, files in os.walk(opdir, topdown=False):
                if not os.listdir(root):
                    os.rmdir(root)
            if not os.listdir(opdir):
                os.rmdir(opdir)
        except (OSError, PermissionError):
            pass
    return {'scanned': scanned, 'removed': removed}


def delete_op(op_id: str) -> bool:
    _init_db()
    conn = _connect()
    cur = conn.cursor()
    cur.execute('SELECT backup_dir FROM ops WHERE id=?', (op_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    bdir = row[0]
    cur.execute('DELETE FROM ops WHERE id=?', (op_id,))
    conn.commit()
    conn.close()
    try:
        if bdir and os.path.exists(bdir):
            # prefer os-native trash if available
            try:
                from send2trash import send2trash  # type: ignore

                send2trash(bdir)
            except Exception:
                shutil.rmtree(bdir)
    except (OSError, shutil.Error):
        pass
    return True
