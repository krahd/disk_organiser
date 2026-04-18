"""Background job helpers for scanning files for duplicates."""

import os
import json
import uuid
import time
from typing import List

try:
    # try package import
    from backend.utils import find_duplicates
except ImportError:
    # allow fallback to local import when running from repo root
    from utils import find_duplicates

BASE = os.path.dirname(__file__)
JOBS_DIR = os.path.join(BASE, 'scan_jobs')
os.makedirs(JOBS_DIR, exist_ok=True)


def _job_path(job_id: str) -> str:
    """Return the file path for a job id."""
    return os.path.join(JOBS_DIR, f"{job_id}.json")


def _cancel_path(job_id: str) -> str:
    return os.path.join(JOBS_DIR, f"{job_id}.cancel")


def background_scan(
    paths: List[str],
    min_size: int = 1,
    max_files: int | None = None,
    job_id: str | None = None,
    max_workers: int | None = None,
):
    """Run a background duplicate scan and persist job status to disk.

    The function records job start/finish/failure to a job file. Callers
    (or a web endpoint) can subsequently inspect progress.
    """
    job_id = job_id or uuid.uuid4().hex
    job_file = _job_path(job_id)
    job = {
        'id': job_id,
        'status': 'started',
        'created_at': time.time(),
        'result': None,
        'progress': {},
    }
    with open(job_file, 'w', encoding='utf-8') as f:
        json.dump(job, f)

    cancel_file = _cancel_path(job_id)

    def _write_status(updated: dict):
        try:
            with open(job_file, 'w', encoding='utf-8') as _f:
                json.dump(updated, _f, default=str)
        except Exception:
            pass

    def progress_cb(data: dict):
        # update progress and persist
        job['progress'] = data
        _write_status(job)
        # check cancellation file for thread-based jobs
        if os.path.exists(cancel_file):
            raise RuntimeError('cancelled')

    try:
        result = find_duplicates(
            paths,
            min_size=min_size,
            max_files=max_files,
            progress_callback=progress_cb,
            max_workers=max_workers,
        )
        job['status'] = 'finished'
        job['finished_at'] = time.time()
        job['result'] = result
    except RuntimeError as e:
        # cancellation requested
        job['status'] = 'cancelled'
        job['error'] = str(e)
    except Exception as e:  # pylint: disable=broad-exception-caught
        job['status'] = 'failed'
        job['error'] = str(e)
    _write_status(job)
    # cleanup cancel file if present
    try:
        if os.path.exists(cancel_file):
            os.remove(cancel_file)
    except Exception:
        pass
    return job


def job_status(job_id: str):
    """Read job status from disk for given job id."""
    job_file = _job_path(job_id)
    if not os.path.exists(job_file):
        return {'error': 'not found'}
    try:
        with open(job_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {'error': 'failed to read job file'}
