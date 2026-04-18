"""Utilities for file hashing, duplicate detection and lightweight visualisation."""

import os
import hashlib
from typing import List, Dict


def file_hash(path: str, chunk_size: int = 8192) -> str:
    """Return SHA-256 hex digest for file at `path` read in chunks."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            h.update(chunk)
    return h.hexdigest()


def find_duplicates(paths: List[str], min_size: int = 1, max_files: int = None) -> List[Dict]:
    """Scan given paths for duplicate files (by content hash).

    Returns a list of groups where each group is a dict {hash, files:[{path,size}]}
    """
    hashes = {}
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
                    h = file_hash(fp)
                    hashes.setdefault(h, []).append({"path": fp, "size": st.st_size})
                    seen += 1
                except (OSError, PermissionError):
                    continue
    result = []
    for h, items in hashes.items():
        if len(items) > 1:
            result.append({"hash": h, "files": items})
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
