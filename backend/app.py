"""Disk Organiser Flask API.

Provides endpoints for duplicates, visualisation, organise operations,
background scans and recycle-bin management.
"""

import os
import importlib.util
import threading
import traceback
import uuid
import shutil

from flask import Flask, jsonify, request
from flask_cors import CORS

# Optional Redis/RQ imports (may not be installed in development environments)
try:
    from redis import Redis  # type: ignore
    from rq import Queue  # type: ignore
    _REDIS_AVAILABLE = True
except ImportError:
    Redis = None  # type: ignore
    Queue = None  # type: ignore
    _REDIS_AVAILABLE = False


def _import_local_module(module_name: str, filename: str):
    """Load a module from the local `backend` directory by filename.

    This helper allows the application to run both as a package and as a
    standalone script by locating modules by path.
    """
    base = os.path.dirname(__file__)
    path = os.path.join(base, filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    store_mod = _import_local_module('store', 'store.py')
    utils_mod = _import_local_module('utils', 'utils.py')
    tasks_mod = _import_local_module('tasks', 'tasks.py')
    op_store_mod = _import_local_module('op_store', 'op_store.py')
    load_config = store_mod.load_config
    save_config = store_mod.save_config
    find_duplicates = utils_mod.find_duplicates
    visualise_path = utils_mod.visualise_path
    background_scan = tasks_mod.background_scan
    job_status = tasks_mod.job_status
    create_op = op_store_mod.create_op
    get_op = op_store_mod.get_op
    update_op = op_store_mod.update_op
    backup_file = op_store_mod.backup_file
    add_executed_action = op_store_mod.add_executed_action
    undo_op = op_store_mod.undo_op
    set_op_status = op_store_mod.set_op_status
    cleanup_recycle = op_store_mod.cleanup_recycle
    list_backups = op_store_mod.list_backups
    delete_op = op_store_mod.delete_op
except (ImportError, FileNotFoundError):
    # final fallback: try package imports if available
    try:
        from backend.store import load_config, save_config
        from backend.utils import find_duplicates, visualise_path
        from backend.tasks import background_scan, job_status
        from backend.op_store import (
            create_op,
            get_op,
            update_op,
            backup_file,
            add_executed_action,
            undo_op,
            set_op_status,
            cleanup_recycle,
            list_backups,
            delete_op,
        )
    except ImportError:
        traceback.print_exc()
        raise

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    """Health-check endpoint for the API."""
    return jsonify({"message": "Disk Organiser API running"})


@app.route('/api/duplicates', methods=['POST'])
def api_find_duplicates():
    """Find duplicate files under given paths.

    POST JSON: {paths: [...], min_size: int, max_files: int}
    """
    data = request.get_json(silent=True) or {}
    paths = data.get('paths') or data.get('path')
    if isinstance(paths, str):
        paths = [paths]
    if not paths:
        # default to current working directory
        paths = [os.getcwd()]
    min_size = int(data.get('min_size', 1))
    max_files = data.get('max_files')
    try:
        max_files = int(max_files) if max_files is not None else None
    except (TypeError, ValueError):
        max_files = None
    duplicates = find_duplicates(paths, min_size=min_size, max_files=max_files)
    return jsonify({"duplicates": duplicates, "count": len(duplicates)})


@app.route('/api/visualisation', methods=['POST'])
def api_visualise():
    """Return a lightweight visualisation summary for a path.

    POST JSON: {path: str, depth: int}
    """
    data = request.get_json(silent=True) or {}
    path = data.get('path') or os.getcwd()
    depth = int(data.get('depth', 2))
    try:
        vis = visualise_path(path, depth=depth)
    except (OSError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"visualisation": vis})


@app.route('/api/organise', methods=['POST'])
def api_organise():
    """Return suggested organise actions (preview) for provided duplicates.

    POST JSON: {duplicates: [...]}
    """
    data = request.get_json(silent=True) or {}
    # Heuristic: keep one file, move other duplicates to a 'Duplicates' folder
    duplicates = data.get('duplicates')
    suggestions = []
    if duplicates and isinstance(duplicates, list):
        for group in duplicates:
            files = group.get('files', [])
            if len(files) <= 1:
                continue
            keep = files[0]['path'] if isinstance(files[0], dict) else files[0]
            moves = []
            for f in files[1:]:
                p = f['path'] if isinstance(f, dict) else f
                dst = os.path.join(os.path.dirname(keep), "Duplicates", os.path.basename(p))
                moves.append({"from": p, "to": dst})
            suggestions.append({"keep": keep, "moves": moves})
    return jsonify({"suggestions": suggestions})


@app.route('/api/organise/preview', methods=['POST'])
def api_organise_preview():
    """Create an operation entry from provided suggestions (preview)."""
    data = request.get_json(silent=True) or {}
    suggestions = data.get('suggestions')
    if not suggestions:
        return jsonify({"error": "missing suggestions"}), 400
    op = create_op(suggestions, metadata={"user": "anonymous"})
    return jsonify({"op": op})


@app.route('/api/organise/remove-preview', methods=['POST'])
def api_organise_remove_preview():
    """Create a remove-preview op that moves duplicates into the op's backup dir."""
    data = request.get_json(silent=True) or {}
    duplicates = data.get('duplicates')
    if not duplicates:
        return jsonify({"error": "missing duplicates"}), 400
    # create op first to reserve a backup_dir
    op = create_op([], metadata={"user": "anonymous"})
    op_id = op['id']
    backup_dir = op['backup_dir']
    suggestions = []
    for group in duplicates:
        files = group.get('files', [])
        if len(files) <= 1:
            continue
        keep = files[0]['path'] if isinstance(files[0], dict) else files[0]
        moves = []
        for f in files[1:]:
            src = f['path'] if isinstance(f, dict) else f
            name = uuid.uuid4().hex + '_' + os.path.basename(src)
            dst = os.path.join(backup_dir, name)
            moves.append({"from": src, "to": dst})
        suggestions.append({"keep": keep, "moves": moves})
    update_op(op_id, suggestions=suggestions)
    return jsonify({"op": get_op(op_id)})


@app.route('/api/organise/execute', methods=['POST'])
def api_organise_execute():
    """Execute the moves recorded in an operation, backing up originals."""
    data = request.get_json(silent=True) or {}
    op_id = data.get('op_id')
    if not op_id:
        return jsonify({"error": "missing op_id"}), 400
    op = get_op(op_id)
    if not op:
        return jsonify({"error": "op not found"}), 404
    # Execute suggested moves, backing up originals first
    executed = []
    for s in op.get('suggestions', []):
        moves = s.get('moves', [])
        for m in moves:
            src = m.get('from')
            dst = m.get('to')
            try:
                if not os.path.exists(src):
                    executed.append({'from': src, 'to': dst, 'status': 'missing'})
                    continue
                # If destination is inside op backup_dir, treat moved file as backup
                op_backup_dir = os.path.abspath(op.get('backup_dir', ''))
                dst_abs = os.path.abspath(dst)
                if op_backup_dir and dst_abs.startswith(op_backup_dir):
                    # move original into recycle/backup location and record that as the backup
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(src, dst)
                    b = dst
                    executed.append({'from': src, 'to': dst, 'backup': b, 'status': 'moved'})
                    add_executed_action(op_id, {'from': src, 'to': dst, 'backup': b})
                else:
                    # normal flow: create a backup copy then move file
                    b = backup_file(op_id, src)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(src, dst)
                    executed.append({'from': src, 'to': dst, 'backup': b, 'status': 'moved'})
                    add_executed_action(op_id, {'from': src, 'to': dst, 'backup': b})
            except (OSError, shutil.Error) as e:
                executed.append({'from': src, 'to': dst, 'status': 'error', 'error': str(e)})
    set_op_status(op_id, 'executed')
    return jsonify({"executed": executed})


@app.route('/api/organise/undo', methods=['POST'])
def api_organise_undo():
    """Undo previously executed operation actions (restore backups)."""
    data = request.get_json(silent=True) or {}
    op_id = data.get('op_id')
    if not op_id:
        return jsonify({"error": "missing op_id"}), 400
    res = undo_op(op_id)
    return jsonify(res)


@app.route('/api/model', methods=['GET', 'POST'])
def api_model():
    """Get or set the selected model for analysis.

    GET returns current model. POST JSON: {model: 'ollama'|'gpt'|...}
    """
    cfg = load_config()
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        model = data.get('model')
        if not model:
            return jsonify({"error": "missing model"}), 400
        save_config({"model": model})
        return jsonify({"status": "Model updated", "model": model})
    return jsonify({"model": cfg.get('model', 'ollama')})


@app.route('/api/preferences', methods=['GET', 'POST'])
def api_preferences():
    """Get or set user preferences.

    GET returns current preferences. POST JSON: {preferences: {..}}
    """
    cfg = load_config()
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        prefs = data.get('preferences') or data
        save_config({"preferences": prefs})
        return jsonify({"status": "Preferences updated", "preferences": prefs})
    return jsonify({"preferences": cfg.get('preferences', {})})


@app.route('/api/scan/start', methods=['POST'])
def api_scan_start():
    """Start a background scan job. Tries RQ/Redis, falls back to a thread.

    POST JSON: {paths: [...], min_size: int, max_files: int}
    """
    data = request.get_json(silent=True) or {}
    paths = data.get('paths') or [os.getcwd()]
    min_size = int(data.get('min_size', 1))
    max_files = data.get('max_files')
    try:
        max_files = int(max_files) if max_files is not None else None
    except (TypeError, ValueError):
        max_files = None

    # attempt to use RQ/Redis if available, otherwise fallback to thread
    if _REDIS_AVAILABLE:
        try:
            redis_conn = Redis()
            q = Queue(connection=redis_conn)
            job = q.enqueue(background_scan, paths, min_size, max_files)
            return jsonify({"job_id": job.get_id(), "backend": "rq"})
        except Exception:  # pylint: disable=broad-exception-caught
            # fallthrough to threaded fallback
            pass

    # fallback: spawn a thread and use tasks.background_scan to write job file
    job_id = uuid.uuid4().hex
    thread = threading.Thread(target=background_scan, args=(
        paths, min_size, max_files, job_id), daemon=True)
    thread.start()
    return jsonify({"job_id": job_id, "backend": "thread"})


@app.route('/api/scan/status/<job_id>', methods=['GET'])
def api_scan_status(job_id):
    """Return job status for a background scan job id."""
    try:
        status = job_status(job_id)
        return jsonify(status)
    except (OSError, ValueError) as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recycle/list', methods=['GET'])
def api_recycle_list():
    """List recycle/backed-up files for review."""
    try:
        data = list_backups()
        return jsonify({'recycle': data})
    except (OSError, ValueError) as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/recycle/cleanup', methods=['POST'])
def api_recycle_cleanup():
    """Remove recycled backups older than `retention_days`."""
    data = request.get_json(silent=True) or {}
    days = int(data.get('retention_days', 30))
    try:
        res = cleanup_recycle(days)
        return jsonify(res)
    except (OSError, ValueError) as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/recycle/delete_op', methods=['POST'])
def api_recycle_delete_op():
    """Delete an operation and its backups from the recycle store."""
    data = request.get_json(silent=True) or {}
    op_id = data.get('op_id')
    if not op_id:
        return jsonify({'error': 'missing op_id'}), 400
    try:
        ok = delete_op(op_id)
        if ok:
            return jsonify({'deleted': op_id})
        return jsonify({'error': 'op not found'}), 404
    except (OSError, shutil.Error) as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
