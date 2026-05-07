"""Integration test: AI suggestion -> preview -> execute -> undo flow
using CI dummy provider.
"""

import importlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

app = importlib.import_module("backend.app")
op_store = importlib.import_module("backend.op_store")


def test_ai_suggest_preview_execute_undo(tmp_path):
    # isolate op storage to temp location to avoid repo pollution
    ops_file = tmp_path / "ops.json"
    backups = tmp_path / "ops_backups"
    backups.mkdir()
    op_store.OPS_FILE = str(ops_file)
    op_store.BACKUP_ROOT = str(backups)

    client = app.app.test_client()

    # select the CI dummy provider via API (triggers reload)
    r = client.post("/api/model", json={"model": "ci_dummy"})
    assert r.status_code == 200

    # create duplicate files
    d = tmp_path / "ai_flow"
    d.mkdir()
    a = d / "a.txt"
    b = d / "b.txt"
    a.write_bytes(b"hello")
    b.write_bytes(b"hello")

    # get duplicates
    r = client.post("/api/duplicates", json={"paths": [str(d)], "min_size": 1})
    assert r.status_code == 200
    dup = r.get_json()
    assert dup.get("count") >= 1

    # ask the AI (ci_dummy) for suggestions
    sres = client.post(
        "/api/organise/suggest", json={"duplicates": dup.get("duplicates")}
    )
    assert sres.status_code == 200
    sj = sres.get_json()
    suggestions = sj.get("suggestions")
    assert suggestions
    # ensure suggestions use AI_Duplicates as ci_dummy indicates
    dst = suggestions[0]["moves"][0]["to"]
    assert "AI_Duplicates" in dst

    # preview -> create op
    pres = client.post("/api/organise/preview", json={"suggestions": suggestions})
    assert pres.status_code == 200
    pj = pres.get_json()
    op = pj.get("op")
    assert op and op.get("id")
    op_id = op["id"]

    # execute
    er = client.post("/api/organise/execute", json={"op_id": op_id})
    assert er.status_code == 200
    ej = er.get_json()
    assert "executed" in ej
    moved = ej["executed"][0]
    assert moved["status"] == "moved"
    # destination should exist, original source should not
    assert os.path.exists(moved["to"])
    assert not os.path.exists(moved["from"])

    # undo (restore)
    ur = client.post("/api/organise/undo", json={"op_id": op_id})
    assert ur.status_code == 200
    uj = ur.get_json()
    assert "restored" in uj
    # original file restored
    assert os.path.exists(moved["from"])
