import importlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

utils = importlib.import_module("backend.utils")
scan_index = importlib.import_module("backend.scan_index")


def test_scan_index_populated(tmp_path):
    # isolate scan index DB to tmp
    scan_index.DB_FILE = str(tmp_path / "scan_index.db")
    scan_index._init_db(scan_index.DB_FILE)

    d = tmp_path / "scan"
    d.mkdir()
    a = d / "a.txt"
    b = d / "b.txt"
    a.write_bytes(b"hello world")
    b.write_bytes(b"hello world")

    groups = utils.find_duplicates([str(d)], min_size=1)
    assert any(len(g["files"]) >= 2 for g in groups)

    # ensure index was populated with full_hash entries
    e = scan_index.get_entry(str(a))
    assert e is not None
    assert e.get("full_hash") is not None
