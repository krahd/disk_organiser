"""Utilities for file hashing, duplicate detection and lightweight visualisation.

Implements a multi-stage duplicate finder:
  1) Group files by size
  2) Compute a small sample hash (first+last bytes) to filter
  3) Compute a full content hash for remaining candidates

This approach reduces the number of expensive full-file hashes on large
collections while remaining deterministic.
"""

import os
import hashlib
import concurrent.futures
from typing import List, Dict
try:
    from backend import scan_index as scan_index_mod
    _SCAN_INDEX_AVAILABLE = True
except Exception:
    scan_index_mod = None
    _SCAN_INDEX_AVAILABLE = False
try:
    import xxhash  # type: ignore
    _XXHASH_AVAILABLE = True
except Exception:
    xxhash = None
    _XXHASH_AVAILABLE = False


def file_hash(path: str, chunk_size: int = 8192) -> str:
    """Return SHA-256 hex digest for file at `path` read in chunks."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            h.update(chunk)
    return h.hexdigest()


def _sample_hash(path: str, sample_size: int = 4096) -> str:
    """Compute a small sample hash combining the first and last samples of the file.

    If the file is smaller than 2 * sample_size, hash the full file instead.
    """
    size = os.path.getsize(path)
    # prefer xxhash for sample hashing if available for speed
    if _XXHASH_AVAILABLE:
        h = xxhash.xxh64()
        size = os.path.getsize(path)
        with open(path, 'rb') as f:
            if size <= sample_size * 2:
                for chunk in iter(lambda: f.read(8192), b''):
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
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
        return h.hexdigest()

    h = hashlib.sha256()
    with open(path, 'rb') as f:
        if size <= sample_size * 2:
            # small file: hash full content
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
            return h.hexdigest()
        # read first sample
        first = f.read(sample_size)
        h.update(first)
        # read last sample
        try:
            f.seek(-sample_size, os.SEEK_END)
            last = f.read(sample_size)
            h.update(last)
        except OSError:
            # fallback: read from current position
            f.seek(0)
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
    return h.hexdigest()


def find_duplicates(
        paths: List[str],
        min_size: int = 1,
        max_files: int = None,
        sample_size: int = 4096,
        progress_callback=None,
        max_workers: int | None = None,
) -> List[Dict]:
    # 1) Walk and group by size
    size_buckets = {}
    seen = 0
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
                    if max_files is not None and seen >= max_files:
                        break
                    size_buckets.setdefault(st.st_size, []).append(fp)
                    seen += 1
                    if progress_callback and seen % 100 == 0:
                        try:
                            progress_callback({'status': 'scanning', 'processed': seen})
                        except Exception:
                            pass
                except (OSError, PermissionError):
                    continue

    result = []
    # 2) For each size bucket, sample-hash and then full-hash where needed
    for size, files in size_buckets.items():
        if len(files) <= 1:
            continue
        # group by sample hash
        sample_map = {}
        for fp in files:
            try:
                # consult scan index to reuse cached sample hash where possible
                entry = None
                if _SCAN_INDEX_AVAILABLE:
                    try:
                        entry = scan_index_mod.get_entry(fp)
                    except Exception:
                        entry = None

                # compute or reuse sample hash
                sh = (
                    entry.get('sample_hash')
                    if entry and entry.get('sample_hash')
                    else _sample_hash(fp, sample_size=sample_size)
                )
                # persist sample hash to index
                if _SCAN_INDEX_AVAILABLE:
                    try:
                        full_hash = entry.get('full_hash') if entry else None
                        scan_index_mod.upsert_entry(
                            fp,
                            size,
                            os.path.getmtime(fp),
                            sample_hash=sh,
                            full_hash=full_hash,
                        )
                    except Exception:
                        pass
                sample_map.setdefault(sh, []).append(fp)
            except (OSError, PermissionError):
                continue
        # for each candidate sample group, compute full hash
        for sh, fpaths in sample_map.items():
            if len(fpaths) <= 1:
                continue
            # compute full hashes in parallel for performance
            full_map = {}
            # helper to compute or reuse full hash for a single file
            # helper to compute or reuse full hash for a single file

            def _compute_full(fp):
                try:
                    entry = None
                    if _SCAN_INDEX_AVAILABLE:
                        try:
                            entry = scan_index_mod.get_entry(fp)
                        except Exception:
                            entry = None
                    if entry and entry.get('full_hash'):
                        return fp, entry.get('full_hash')
                    fh = file_hash(fp)
                    if _SCAN_INDEX_AVAILABLE:
                        try:
                            scan_index_mod.set_full_hash(fp, fh)
                        except Exception:
                            pass
                    return fp, fh
                except Exception:
                    return fp, None

            to_hash = list(fpaths)
            total = len(to_hash)
            hashed = 0
            # respect explicit max_workers if provided, otherwise fallback to a
            # conservative heuristic. Allow overriding via `MAX_HASH_WORKERS`
            # environment variable for advanced deployments.
            if max_workers is None:
                env_val = os.getenv('MAX_HASH_WORKERS')
                if env_val:
                    try:
                        computed_workers = max(1, min(int(env_val), total))
                    except Exception:
                        computed_workers = max(1, min((os.cpu_count() or 1) * 2, total, 32))
                else:
                    # default: 2 * cpu_count, capped to 32
                    computed_workers = max(1, min((os.cpu_count() or 1) * 2, total, 32))
            else:
                computed_workers = max(1, min(int(max_workers), total))
            with concurrent.futures.ThreadPoolExecutor(max_workers=computed_workers) as exe:
                futures = {exe.submit(_compute_full, fp): fp for fp in to_hash}
                for fut in concurrent.futures.as_completed(futures):
                    fp = futures[fut]
                    try:
                        fp_ret, fh = fut.result()
                    except Exception:
                        fp_ret, fh = fp, None
                    hashed += 1
                    if fh:
                        full_map.setdefault(fh, []).append(fp_ret)
                    if progress_callback:
                        try:
                            info = {'status': 'hashing', 'file': fp_ret,
                                    'processed': hashed, 'total': total}
                            progress_callback(info)
                        except Exception:
                            pass
            for fh, fps in full_map.items():
                if len(fps) > 1:
                    items = []
                    for p in fps:
                        try:
                            items.append({'path': p, 'size': os.path.getsize(p)})
                        except (OSError, PermissionError):
                            continue
                    result.append({'hash': fh, 'files': items})
    return result


def visualise_path(path: str, depth: int = 2, max_entries: int = 50) -> Dict:
    """Return a lightweight directory summary for visualization.

    Structure: {path, size, files, children: [{name,path,size,files,children}]}
    """
    def scan(p: str, d: int):
        size = 0
        files = 0
        children = []
        try:
            with os.scandir(p) as it:
                for e in it:
                    try:
                        if e.is_symlink():
                            continue
                        if e.is_file():
                            files += 1
                            size += e.stat().st_size
                        elif e.is_dir():
                            if d > 0:
                                child = scan(e.path, d - 1)
                                children.append({
                                    "name": e.name,
                                    "path": e.path,
                                    "size": child["size"],
                                    "files": child["files"],
                                    "children": child.get("children", []),
                                })
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            return {"size": 0, "files": 0, "children": []}
        return {"size": size, "files": files, "children": children}

    root = os.path.abspath(path)
    data = scan(root, depth)
    # sort children by size desc for top-level visibility
    data_children = sorted(data.get("children", []), key=lambda x: x.get("size", 0), reverse=True)
    return {
        "path": root,
        "size": data.get("size", 0),
        "files": data.get("files", 0),
        "children": data_children[:max_entries],
    }
