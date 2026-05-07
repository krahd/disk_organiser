import importlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

op_store = importlib.import_module("backend.op_store")


def test_create_backup_and_record(tmp_path):
    # redirect ops storage to tmp path to avoid touching repo files
    op_store.DB_FILE = str(tmp_path / "ops.db")
    op_store.BACKUP_ROOT = str(tmp_path / "ops_backups")

    # create a source file to back up
    src = tmp_path / "file.txt"
    src.write_text("hello world")

    # create op and backup the file
    op = op_store.create_op([], metadata={"test": True})
    assert op and op.get("id")
    bpath = op_store.backup_file(op["id"], str(src))
    assert bpath is not None
    assert os.path.exists(bpath)

    # record executed action and verify it's stored
    action = {"from": str(src), "to": "/tmp/dst", "backup": bpath}
    ok = op_store.add_executed_action(op["id"], action)
    assert ok
    loaded = op_store.get_op(op["id"])
    assert loaded is not None
    assert "executed_actions" in loaded
    assert loaded["executed_actions"][0]["backup"] == bpath
