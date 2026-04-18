"""Disk Organiser Flask API.

Provides endpoints for duplicates, visualisation, organise operations,
background scans and recycle-bin management.
"""

# pylint: disable=broad-exception-caught,invalid-name,import-outside-toplevel,
# pylint: disable=too-many-locals,too-many-nested-blocks,redefined-outer-name,
# pylint: disable=unused-variable,duplicate-code

import importlib.util
import json
import logging
import os
import shutil
import threading
import time
import traceback
import uuid

from flask import Flask, Response, jsonify, request, stream_with_context
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
    store_mod = _import_local_module("store", "store.py")
    utils_mod = _import_local_module("utils", "utils.py")
    tasks_mod = _import_local_module("tasks", "tasks.py")
    op_store_mod = _import_local_module("op_store", "op_store.py")
    fs_ops_mod = _import_local_module("fs_ops", "fs_ops.py")
    load_config = store_mod.load_config
    save_config = store_mod.save_config
    find_duplicates = utils_mod.find_duplicates
    visualise_path = utils_mod.visualise_path
    background_scan = tasks_mod.background_scan
    job_status = tasks_mod.job_status
    create_op = op_store_mod.create_op
    get_op = op_store_mod.get_op
    update_op = op_store_mod.update_op
    list_ops = op_store_mod.list_ops
    backup_file = op_store_mod.backup_file
    add_executed_action = op_store_mod.add_executed_action
    undo_op = op_store_mod.undo_op
    set_op_status = op_store_mod.set_op_status
    cleanup_recycle = op_store_mod.cleanup_recycle
    list_backups = op_store_mod.list_backups
    delete_op = op_store_mod.delete_op
    try:
        scan_index_mod = _import_local_module("scan_index", "scan_index.py")
    except Exception:
        scan_index_mod = None
except (ImportError, FileNotFoundError):
    # final fallback: try package imports if available
    try:
        from backend import fs_ops as fs_ops_mod
        from backend.op_store import (
            add_executed_action,
            backup_file,
            cleanup_recycle,
            create_op,
            delete_op,
            get_op,
            list_backups,
            list_ops,
            set_op_status,
            undo_op,
            update_op,
        )
        from backend.store import load_config, save_config
        from backend.tasks import background_scan, job_status
        from backend.utils import find_duplicates, visualise_path

        try:
            from backend import scan_index as scan_index_mod
        except Exception:
            scan_index_mod = None
    except ImportError:
        traceback.print_exc()
        raise

# Attempt to load the optional model client. If unavailable, `model_client`
# will be `None` and endpoints should fall back to a safe heuristic.
try:
    model_client_mod = _import_local_module("model_client", "model_client.py")
    ModelClient = model_client_mod.ModelClient
    # instantiate with the configured model (if any)
    try:
        cfg = load_config()
        model_client = ModelClient(provider_name=cfg.get("model"))
    except Exception:
        model_client = ModelClient()
except Exception:
    try:
        from backend.model_client import ModelClient  # type: ignore

        try:
            cfg = load_config()
            model_client = ModelClient(provider_name=cfg.get("model"))
        except Exception:
            model_client = ModelClient()
    except Exception:
        model_client = None
# Ensure model_client reflects current saved config if available
try:
    if model_client is not None and hasattr(model_client, "reload"):
        cfg = load_config()
        model_client.reload(cfg.get("model"))
except Exception:
    pass

app = Flask(__name__)
CORS(app)
logger = logging.getLogger(__name__)
MAINT_FILE = os.path.join(os.path.dirname(__file__), "maintenance_status.json")


@app.route("/")
def index():
    """Health-check endpoint for the API."""
    return jsonify({"message": "Disk Organiser API running"})


@app.route("/api/duplicates", methods=["POST"])
def api_find_duplicates():
    """Find duplicate files under given paths.

    POST JSON: {paths: [...], min_size: int, max_files: int}
    """
    data = request.get_json(silent=True) or {}
    paths = data.get("paths") or data.get("path")
    if isinstance(paths, str):
        paths = [paths]
    if not paths:
        # default to current working directory
        paths = [os.getcwd()]
    min_size = int(data.get("min_size", 1))
    max_files = data.get("max_files")
    max_workers = data.get("max_workers")
    try:
        max_files = int(max_files) if max_files is not None else None
    except (TypeError, ValueError):
        max_files = None
    try:
        max_workers = int(max_workers) if max_workers is not None else None
    except (TypeError, ValueError):
        max_workers = None
    duplicates = find_duplicates(
        paths, min_size=min_size, max_files=max_files, max_workers=max_workers
    )
    return jsonify({"duplicates": duplicates, "count": len(duplicates)})


@app.route("/api/visualisation", methods=["POST"])
def api_visualise():
    """Return a lightweight visualisation summary for a path.

    POST JSON: {path: str, depth: int}
    """
    data = request.get_json(silent=True) or {}
    path = data.get("path") or os.getcwd()
    depth = int(data.get("depth", 2))
    try:
        vis = visualise_path(path, depth=depth)
    except (OSError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"visualisation": vis})


@app.route("/api/organise", methods=["POST"])
def api_organise():
    """Return suggested organise actions (preview) for provided duplicates.

    POST JSON: {duplicates: [...]}
    """
    data = request.get_json(silent=True) or {}
    # Heuristic: keep one file, move other duplicates to a 'Duplicates' folder
    duplicates = data.get("duplicates")
    suggestions = []
    if duplicates and isinstance(duplicates, list):
        for group in duplicates:
            files = group.get("files", [])
            if len(files) <= 1:
                continue
            keep = files[0]["path"] if isinstance(files[0], dict) else files[0]
            moves = []
            for f in files[1:]:
                p = f["path"] if isinstance(f, dict) else f
                dst = os.path.join(
                    os.path.dirname(keep), "Duplicates", os.path.basename(p)
                )
                moves.append({"from": p, "to": dst})
            suggestions.append({"keep": keep, "moves": moves})
    return jsonify({"suggestions": suggestions})


@app.route("/api/organise/suggest", methods=["POST"])
def api_organise_suggest():
    """Return AI-assisted organise suggestions for provided duplicates.

    POST JSON: {duplicates: [...]}
    If an external model client is configured it will be used; otherwise a
    deterministic heuristic fallback is returned so the endpoint remains safe
    and testable in environments without model integrations.
    """
    data = request.get_json(silent=True) or {}
    duplicates = data.get("duplicates")
    if not duplicates:
        return jsonify({"error": "missing duplicates"}), 400

    if model_client is not None:
        try:
            suggestions = model_client.suggest_organise(duplicates)
        except Exception:
            logger.debug("Model client suggest failed", exc_info=True)
            # model failure: fall back to heuristic
            suggestions = []
            for group in duplicates:
                files = group.get("files", [])
                if len(files) <= 1:
                    continue
                keep = files[0]["path"] if isinstance(files[0], dict) else files[0]
                moves = []
                for f in files[1:]:
                    p = f["path"] if isinstance(f, dict) else f
                    dst = os.path.join(
                        os.path.dirname(keep), "Duplicates", os.path.basename(p)
                    )
                    moves.append({"from": p, "to": dst})
                suggestions.append({"keep": keep, "moves": moves})
    else:
        # deterministic heuristic
        suggestions = []
        for group in duplicates:
            files = group.get("files", [])
            if len(files) <= 1:
                continue
            keep = files[0]["path"] if isinstance(files[0], dict) else files[0]
            moves = []
            for f in files[1:]:
                p = f["path"] if isinstance(f, dict) else f
                dst = os.path.join(
                    os.path.dirname(keep), "Duplicates", os.path.basename(p)
                )
                moves.append({"from": p, "to": dst})
            suggestions.append({"keep": keep, "moves": moves})

    return jsonify({"suggestions": suggestions})


@app.route("/api/organise/preview", methods=["POST"])
def api_organise_preview():
    """Create an operation entry from provided suggestions (preview)."""
    data = request.get_json(silent=True) or {}
    suggestions = data.get("suggestions")
    if not suggestions:
        return jsonify({"error": "missing suggestions"}), 400
    op = create_op(suggestions, metadata={"user": "anonymous"})
    return jsonify({"op": op})


@app.route("/api/organise/remove-preview", methods=["POST"])
def api_organise_remove_preview():
    """Create a remove-preview op that moves duplicates into the op's backup dir."""
    data = request.get_json(silent=True) or {}
    duplicates = data.get("duplicates")
    if not duplicates:
        return jsonify({"error": "missing duplicates"}), 400
    # create op first to reserve a backup_dir
    op = create_op([], metadata={"user": "anonymous"})
    op_id = op["id"]
    backup_dir = op["backup_dir"]
    suggestions = []
    for group in duplicates:
        files = group.get("files", [])
        if len(files) <= 1:
            continue
        keep = files[0]["path"] if isinstance(files[0], dict) else files[0]
        moves = []
        for f in files[1:]:
            src = f["path"] if isinstance(f, dict) else f
            name = uuid.uuid4().hex + "_" + os.path.basename(src)
            dst = os.path.join(backup_dir, name)
            moves.append({"from": src, "to": dst})
        suggestions.append({"keep": keep, "moves": moves})
    update_op(op_id, suggestions=suggestions)
    return jsonify({"op": get_op(op_id)})


@app.route("/api/organise/execute", methods=["POST"])
def api_organise_execute():
    """Execute the moves recorded in an operation, backing up originals."""
    data = request.get_json(silent=True) or {}
    op_id = data.get("op_id")
    if not op_id:
        return jsonify({"error": "missing op_id"}), 400
    op = get_op(op_id)
    if not op:
        return jsonify({"error": "op not found"}), 404
    dry_run = bool(data.get("dry_run", False))
    if dry_run:
        # Produce a non-destructive preview of actions without touching disk.
        try:
            actions = fs_ops_mod.preview_suggestions(
                op.get("suggestions", []), op.get("backup_dir")
            )
            summary = fs_ops_mod.summarize_actions(actions)
        except Exception:
            return jsonify({"error": "failed to generate preview"}), 500
        return jsonify(
            {
                "op_id": op_id,
                "dry_run": True,
                "preview": actions,
                "summary": summary,
            }
        )
    # Execute suggested moves, backing up originals first
    executed = []
    for s in op.get("suggestions", []):
        moves = s.get("moves", [])
        for m in moves:
            src = m.get("from")
            dst = m.get("to")
            try:
                if not os.path.exists(src):
                    executed.append({"from": src, "to": dst, "status": "missing"})
                    continue
                # If destination is inside op backup_dir, treat moved file as backup
                op_backup_dir = os.path.abspath(op.get("backup_dir", ""))
                dst_abs = os.path.abspath(dst)
                if op_backup_dir and dst_abs.startswith(op_backup_dir):
                    # move original into recycle/backup location
                    # and record that as the backup
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(src, dst)
                    b = dst
                    executed.append(
                        {"from": src, "to": dst, "backup": b, "status": "moved"}
                    )
                    add_executed_action(op_id, {"from": src, "to": dst, "backup": b})
                else:
                    # normal flow: create a backup copy then move file
                    b = backup_file(op_id, src)
                    if not b:
                        # backup failed — do not move the original to avoid data loss
                        executed.append(
                            {
                                "from": src,
                                "to": dst,
                                "backup": None,
                                "status": "backup_failed",
                            }
                        )
                        continue
                    try:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.move(src, dst)
                        executed.append(
                            {"from": src, "to": dst, "backup": b, "status": "moved"}
                        )
                        add_executed_action(
                            op_id, {"from": src, "to": dst, "backup": b}
                        )
                    except (OSError, shutil.Error) as e:
                        executed.append(
                            {"from": src, "to": dst, "status": "error", "error": str(e)}
                        )
            except (OSError, shutil.Error) as e:
                executed.append(
                    {"from": src, "to": dst, "status": "error", "error": str(e)}
                )
    set_op_status(op_id, "executed")
    return jsonify({"executed": executed})


@app.route("/api/organise/undo", methods=["POST"])
def api_organise_undo():
    """Undo previously executed operation actions (restore backups)."""
    data = request.get_json(silent=True) or {}
    op_id = data.get("op_id")
    if not op_id:
        return jsonify({"error": "missing op_id"}), 400
    dry_run = bool(data.get("dry_run", False))
    if dry_run:
        # produce a preview of restore actions without moving files
        op = get_op(op_id)
        if not op:
            return jsonify({"error": "op not found"}), 404
        acts = op.get("executed_actions", [])
        # actions were recorded in seq ascending; undo will restore in desc order
        preview = []
        for a in reversed(acts):
            try:
                action = a if isinstance(a, dict) else a.get("raw")
            except Exception:
                action = a
            backup = action.get("backup") if isinstance(action, dict) else None
            orig = action.get("from") if isinstance(action, dict) else None
            if backup and orig:
                preview.append(
                    fs_ops_mod.preview_move_action(backup, orig, op.get("backup_dir"))
                )
            else:
                preview.append(
                    {
                        "action": "restore",
                        "from": backup,
                        "to": orig,
                        "status": "unknown",
                    }
                )
        summary = fs_ops_mod.summarize_actions(preview)
        return jsonify(
            {
                "op_id": op_id,
                "dry_run": True,
                "preview": preview,
                "summary": summary,
            }
        )
    res = undo_op(op_id)
    return jsonify(res)


@app.route("/api/model", methods=["GET", "POST"])
def api_model():
    """Get or set the selected model for analysis.

    GET returns current model. POST JSON: {model: 'ollama'|'gpt'|...}
    """
    cfg = load_config()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        model = data.get("model")
        if not model:
            return jsonify({"error": "missing model"}), 400
        dry_run = bool(data.get("dry_run", False))
        save_config({"model": model}, dry_run=dry_run)
        # reload model client with the newly selected provider
        try:
            if (
                not dry_run
                and model_client is not None
                and hasattr(model_client, "reload")
            ):
                model_client.reload(model)
        except Exception:
            # don't fail the request if reload fails
            pass
        return jsonify({"status": "Model updated", "model": model})
    return jsonify({"model": cfg.get("model", "ollama")})


@app.route("/api/preferences", methods=["GET", "POST"])
def api_preferences():
    """Get or set user preferences.

    GET returns current preferences. POST JSON: {preferences: {..}}
    """
    cfg = load_config()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        prefs = data.get("preferences") or data
        dry_run = bool(data.get("dry_run", False))
        save_config({"preferences": prefs}, dry_run=dry_run)
        return jsonify({"status": "Preferences updated", "preferences": prefs})
    return jsonify({"preferences": cfg.get("preferences", {})})


@app.route("/api/scan/start", methods=["POST"])
def api_scan_start():
    """Start a background scan job. Tries RQ/Redis, falls back to a thread.

    POST JSON: {paths: [...], min_size: int, max_files: int}
    """
    data = request.get_json(silent=True) or {}
    paths = data.get("paths") or [os.getcwd()]
    min_size = int(data.get("min_size", 1))
    max_files = data.get("max_files")
    max_workers = data.get("max_workers")
    try:
        max_files = int(max_files) if max_files is not None else None
    except (TypeError, ValueError):
        max_files = None
    try:
        max_workers = int(max_workers) if max_workers is not None else None
    except (TypeError, ValueError):
        max_workers = None

    dry_run = bool(data.get("dry_run", False))
    # attempt to use RQ/Redis if available and not a dry_run
    # otherwise fall back to threaded execution
    if _REDIS_AVAILABLE and not dry_run:
        try:
            redis_conn = Redis()
            q = Queue(connection=redis_conn)
            # enqueue positional args: paths, min_size, max_files,
            # job_id(None), max_workers
            job = q.enqueue(
                background_scan, paths, min_size, max_files, None, max_workers
            )
            return jsonify({"job_id": job.get_id(), "backend": "rq"})
        except Exception:  # pylint: disable=broad-exception-caught
            # fallthrough to threaded fallback
            pass

    # fallback: spawn a thread and use tasks.background_scan
    # to write job file (unless dry_run)
    job_id = uuid.uuid4().hex
    thread = threading.Thread(
        target=background_scan,
        args=(paths, min_size, max_files, job_id, max_workers, dry_run),
        daemon=True,
    )
    thread.start()
    return jsonify({"job_id": job_id, "backend": "thread", "dry_run": dry_run})


@app.route("/api/scan/status/<job_id>", methods=["GET"])
def api_scan_status(job_id):
    """Return job status for a background scan job id."""
    try:
        status = job_status(job_id)
        return jsonify(status)
    except (OSError, ValueError) as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan/events/<job_id>")
def api_scan_events(job_id):
    """SSE endpoint streaming JSON job updates for a given job id."""
    job_file = os.path.join(os.path.dirname(__file__), "scan_jobs", f"{job_id}.json")

    def event_stream():
        last_mtime = 0
        while True:
            if not os.path.exists(job_file):
                yield "data: {}\n\n"
                time.sleep(0.5)
                continue
            try:
                mtime = os.path.getmtime(job_file)
            except Exception:
                mtime = last_mtime
            if mtime > last_mtime:
                try:
                    with open(job_file, "r", encoding="utf-8") as f:
                        data = f.read()
                    # send as SSE data
                    yield f"data: {data}\n\n"
                    last_mtime = mtime
                except Exception:
                    pass
            time.sleep(0.5)

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")


@app.route("/api/scan/cancel", methods=["POST"])
def api_scan_cancel():
    """Request cancellation for a background scan job.

    Tries to cancel RQ jobs if Redis is available; otherwise creates a
    cancel file that threaded jobs check for.
    POST JSON: {job_id: str}
    """
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "missing job_id"}), 400
    # best-effort: attempt to cancel RQ job
    cancelled = False
    if _REDIS_AVAILABLE:
        try:
            redis_conn = Redis()
            from rq.job import Job

            try:
                job = Job.fetch(job_id, connection=redis_conn)
                # try to delete job from queue; may not stop running job
                job.delete()
                cancelled = True
            except Exception:
                # if fetch/delete fails, continue to write cancel file
                cancelled = False
        except Exception:
            cancelled = False

    # write cancel file so thread fallback can detect
    try:
        cancel_path = os.path.join(
            os.path.dirname(__file__), "scan_jobs", f"{job_id}.cancel"
        )
        with open(cancel_path, "w", encoding="utf-8"):
            pass
        cancelled = True
    except Exception:
        pass

    if cancelled:
        return jsonify({"cancelled": job_id})
    return jsonify({"error": "failed to cancel"}), 500


@app.route("/api/recycle/list", methods=["GET"])
def api_recycle_list():
    """List recycle/backed-up files for review."""
    try:
        data = list_backups()
        return jsonify({"recycle": data})
    except (OSError, ValueError) as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ops", methods=["GET"])
def api_list_ops():
    """Return all stored operations."""
    try:
        ops = list_ops()
        return jsonify({"ops": ops})
    except (OSError, ValueError) as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/op/<op_id>", methods=["GET"])
def api_get_op(op_id):
    """Return a single operation by id."""
    try:
        op = get_op(op_id)
        if not op:
            return jsonify({"error": "op not found"}), 404
        return jsonify({"op": op})
    except (OSError, ValueError) as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/recycle/cleanup", methods=["POST"])
def api_recycle_cleanup():
    """Remove recycled backups older than `retention_days`."""
    data = request.get_json(silent=True) or {}
    days = int(data.get("retention_days", 30))
    dry_run = bool(data.get("dry_run", False))
    try:
        if dry_run:
            # simulate cleanup by listing backups older than cutoff
            now = time.time()
            cutoff = now - (days * 24 * 3600)
            ops = list_backups()
            to_remove = []
            total_size = 0
            for opid, info in ops.items():
                for f in info.get("files", []):
                    if f.get("mtime") and f.get("mtime") < cutoff:
                        to_remove.append(f)
                        try:
                            total_size += int(f.get("size") or 0)
                        except Exception:
                            pass
            return jsonify(
                {
                    "dry_run": True,
                    "removed_count": len(to_remove),
                    "total_bytes": total_size,
                    "files": to_remove,
                }
            )
        res = cleanup_recycle(days)
        return jsonify(res)
    except (OSError, ValueError) as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/recycle/delete_op", methods=["POST"])
def api_recycle_delete_op():
    """Delete an operation and its backups from the recycle store."""
    data = request.get_json(silent=True) or {}
    op_id = data.get("op_id")
    if not op_id:
        return jsonify({"error": "missing op_id"}), 400
    dry_run = bool(data.get("dry_run", False))
    try:
        if dry_run:
            op = get_op(op_id)
            if not op:
                return jsonify({"error": "op not found"}), 404
            bdir = op.get("backup_dir")
            files = []
            if bdir and os.path.exists(bdir):
                for root, _, fns in os.walk(bdir):
                    for fn in fns:
                        fp = os.path.join(root, fn)
                        try:
                            files.append(
                                {
                                    "path": fp,
                                    "size": os.path.getsize(fp),
                                    "mtime": os.path.getmtime(fp),
                                }
                            )
                        except (OSError, PermissionError):
                            continue
            return jsonify({"op_id": op_id, "dry_run": True, "files": files})
        ok = delete_op(op_id)
        if ok:
            return jsonify({"deleted": op_id})
        return jsonify({"error": "op not found"}), 404
    except (OSError, shutil.Error) as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan_index/stats", methods=["GET"])
def api_scan_index_stats():
    """Return basic scan-index statistics."""
    if "scan_index_mod" not in globals() or scan_index_mod is None:
        return jsonify({"error": "scan index not available"}), 404
    try:
        return jsonify(scan_index_mod.stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan_index/rebuild", methods=["POST"])
def api_scan_index_rebuild():
    """Rebuild sample hashes for provided paths into the scan index."""
    if "scan_index_mod" not in globals() or scan_index_mod is None:
        return jsonify({"error": "scan index not available"}), 404
    data = request.get_json(silent=True) or {}
    paths = data.get("paths") or [os.getcwd()]
    min_size = int(data.get("min_size", 1))
    sample_size = int(data.get("sample_size", 4096))
    try:
        res = scan_index_mod.rebuild_index(
            paths, min_size=min_size, sample_size=sample_size
        )
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan_index/rebuild_async", methods=["POST"])
def api_scan_index_rebuild_async():
    """Start a background rebuild of the scan index (returns job id).

    POST JSON: {paths: [...], min_size: int, sample_size: int}
    """
    if "scan_index_mod" not in globals() or scan_index_mod is None:
        return jsonify({"error": "scan index not available"}), 404
    data = request.get_json(silent=True) or {}
    paths = data.get("paths") or [os.getcwd()]
    min_size = int(data.get("min_size", 1))
    sample_size = int(data.get("sample_size", 4096))

    # attempt to use RQ/Redis if available
    # otherwise fallback to thread
    if _REDIS_AVAILABLE:
        try:
            redis_conn = Redis()
            q = Queue(connection=redis_conn)
            job = q.enqueue(
                tasks_mod.rebuild_index_job, paths, min_size, sample_size, None
            )
            return jsonify({"job_id": job.get_id(), "backend": "rq"})
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    job_id = uuid.uuid4().hex
    thread = threading.Thread(
        target=tasks_mod.rebuild_index_job,
        args=(paths, min_size, sample_size, job_id),
        daemon=True,
    )
    thread.start()
    return jsonify({"job_id": job_id, "backend": "thread"})


@app.route("/api/scan_index/prune", methods=["POST"])
def api_scan_index_prune():
    """Prune scan index entries by retention days and/or max entries."""
    if "scan_index_mod" not in globals() or scan_index_mod is None:
        return jsonify({"error": "scan index not available"}), 404
    data = request.get_json(silent=True) or {}
    retention_days = data.get("retention_days")
    max_entries = data.get("max_entries")
    try:
        if retention_days is not None:
            retention_days = int(retention_days)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid retention_days"}), 400
    try:
        if max_entries is not None:
            max_entries = int(max_entries)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid max_entries"}), 400
    dry_run = bool(data.get("dry_run", False))
    try:
        res = scan_index_mod.prune(
            retention_days=retention_days, max_entries=max_entries, dry_run=dry_run
        )
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/maintenance/status", methods=["GET"])
def api_maintenance_status():
    """Return last maintenance run status persisted by the maintenance loop."""
    try:
        if os.path.exists(MAINT_FILE):
            with open(MAINT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"status": "ok", "maintenance": data})
        return jsonify({"status": "unknown", "maintenance": None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/maintenance/run", methods=["POST"])
def api_maintenance_run():
    """Trigger an immediate maintenance prune run and persist status.

    POST JSON: {retention_days: int, max_entries: int}
    """
    if "scan_index_mod" not in globals() or scan_index_mod is None:
        return jsonify({"error": "scan index not available"}), 404
    data = request.get_json(silent=True) or {}
    retention_days = data.get("retention_days")
    max_entries = data.get("max_entries")
    try:
        if retention_days is not None:
            retention_days = int(retention_days)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid retention_days"}), 400
    try:
        if max_entries is not None:
            max_entries = int(max_entries)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid max_entries"}), 400

    try:
        dry_run = bool(data.get("dry_run", False))
        res = scan_index_mod.prune(
            retention_days=retention_days, max_entries=max_entries, dry_run=dry_run
        )
        status = {"timestamp": time.time(), "status": "ok", "result": res}
        try:
            if not dry_run:
                with open(MAINT_FILE, "w", encoding="utf-8") as mf:
                    json.dump(status, mf)
        except Exception:
            logger.exception("Failed to persist maintenance status")
        return jsonify({"status": "ok", "result": res, "dry_run": dry_run})
    except Exception as e:
        status = {"timestamp": time.time(), "status": "error", "error": str(e)}
        try:
            if not bool(data.get("dry_run", False)):
                with open(MAINT_FILE, "w", encoding="utf-8") as mf:
                    json.dump(status, mf)
        except Exception:
            logger.exception("Failed to persist maintenance status")
        return jsonify({"error": str(e)}), 500


def _maintenance_loop():
    """Background maintenance loop that optionally runs index prune.

    Reads configuration via `load_config()` and, when enabled, calls the
    `scan_index.prune` API at the configured interval. This runs in a
    daemon thread so it won't block application shutdown in simple setups.
    """
    while True:
        try:
            cfg = load_config()
            maint = cfg.get("maintenance", {}) or {}
            enabled = bool(maint.get("enabled", False))
            retention_days = maint.get("prune_days", 30)
            max_entries = maint.get("prune_max_entries")
            interval_hours = float(maint.get("interval_hours", 24))
            last_result = {"timestamp": time.time(), "status": "idle"}
            if enabled and scan_index_mod:
                try:
                    logger.info(
                        "Running scheduled scan-index prune "
                        "(retention_days=%s, max_entries=%s)",
                        retention_days,
                        max_entries,
                    )
                    res = scan_index_mod.prune(
                        retention_days=retention_days, max_entries=max_entries
                    )
                    last_result = {
                        "timestamp": time.time(),
                        "status": "ok",
                        "result": res,
                    }
                except Exception as exc:
                    logger.exception("Scheduled scan-index prune failed")
                    last_result = {
                        "timestamp": time.time(),
                        "status": "error",
                        "error": str(exc),
                    }
            # persist last_result so UI can show maintenance outcome
            try:
                with open(MAINT_FILE, "w", encoding="utf-8") as mf:
                    json.dump(last_result, mf)
            except Exception:
                logger.exception("Failed to write maintenance status")
            # sleep until next run
            time.sleep(max(1.0, interval_hours) * 3600.0)
        except Exception:
            # if something unexpected happens, back off for an hour
            logger.exception("Maintenance loop encountered an error")
            try:
                with open(MAINT_FILE, "w", encoding="utf-8") as mf:
                    json.dump(
                        {
                            "timestamp": time.time(),
                            "status": "error",
                            "error": "maintenance loop crash",
                        },
                        mf,
                    )
            except Exception:
                pass
            time.sleep(3600.0)


# start maintenance thread (daemon) so it doesn't block shutdown
try:
    maint_thread = threading.Thread(target=_maintenance_loop, daemon=True)
    maint_thread.start()
except Exception:
    logger.exception("Failed to start maintenance thread")


if __name__ == "__main__":
    app.run(debug=True)
