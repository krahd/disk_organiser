"""Operation store for preview/execute/undo lifecycle and backup management."""

import json
import os
import time
import uuid
import shutil

BASE = os.path.dirname(__file__)
OPS_FILE = os.path.join(BASE, 'ops.json')
BACKUP_ROOT = os.path.join(BASE, 'ops_backups')


def _ensure_dirs():
    """Ensure required directories for operation backups exist."""
    os.makedirs(BACKUP_ROOT, exist_ok=True)


def _load_ops():
    if not os.path.exists(OPS_FILE):
        return {}
    try:
        with open(OPS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_ops(ops: dict):
    with open(OPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(ops, f, indent=2)


def create_op(suggestions: list, metadata: dict | None = None, op_id: str | None = None) -> dict:
    """Create a new operation entry and reserve a backup directory."""
    _ensure_dirs()
    ops = _load_ops()
    if not op_id:
        op_id = uuid.uuid4().hex
    backup_dir = os.path.join(BACKUP_ROOT, op_id)
    os.makedirs(backup_dir, exist_ok=True)
    entry = {
        'id': op_id,
        'suggestions': suggestions,
        'metadata': metadata or {},
        'status': 'preview',
        'created_at': time.time(),
        'backup_dir': backup_dir,
        'executed_actions': []
    }
    ops[op_id] = entry
    _save_ops(ops)
    return entry


def get_op(op_id: str) -> dict | None:
    """Return operation entry by id, or None if not found."""
    ops = _load_ops()
    return ops.get(op_id)


def update_op(op_id: str, **kwargs) -> dict | None:
    """Update fields on an existing operation entry and persist."""
    ops = _load_ops()
    if op_id not in ops:
        return None
    ops[op_id].update(kwargs)
    _save_ops(ops)
    return ops[op_id]


def list_ops() -> dict:
    """Return the mapping of op_id to operation entries."""
    return _load_ops()


def list_backups() -> dict:
    """Return a mapping of op_id to list of backup files with metadata."""
    ops = _load_ops()
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
    """Set the status for an operation entry and persist."""
    ops = _load_ops()
    if op_id in ops:
        ops[op_id]['status'] = status
        _save_ops(ops)
        return True
    return False


def add_executed_action(op_id: str, action: dict):
    """Append an executed action to an operation for later undo."""
    ops = _load_ops()
    if op_id in ops:
        ops[op_id].setdefault('executed_actions', []).append(action)
        _save_ops(ops)
        return True
    return False


def _relpath_to_backup(backup_dir: str, src_path: str) -> str:
    """Create a unique backup path for `src_path` inside `backup_dir`."""
    name = uuid.uuid4().hex + '_' + os.path.basename(src_path)
    return os.path.join(backup_dir, name)


def backup_file(op_id: str, src_path: str) -> str | None:
    """Copy a file into the op's backup directory and return the backup path.

    Returns None on failure.
    """
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
    """Restore executed actions for an operation by moving backups back to originals."""
    op = get_op(op_id)
    if not op:
        return {'error': 'not found'}
    actions = op.get('executed_actions', [])
    results = []
    for a in reversed(actions):
        # each action expected to have 'from','to','backup'
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
    set_op_status(op_id, 'reverted')
    return {'restored': results}


def cleanup_recycle(retention_days: int = 30) -> dict:
    """Remove files in BACKUP_ROOT older than retention_days."""
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
    """Delete an operation entry and its backup directory."""
    ops = _load_ops()
    if op_id not in ops:
        return False
    op = ops.pop(op_id)
    _save_ops(ops)
    # remove backup dir
    bdir = op.get('backup_dir')
    try:
        if bdir and os.path.exists(bdir):
            shutil.rmtree(bdir)
    except (OSError, shutil.Error):
        pass
    return True
