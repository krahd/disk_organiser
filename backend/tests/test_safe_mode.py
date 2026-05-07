import importlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

app = importlib.import_module("backend.app")


def test_organise_execute_dry_run(tmp_path):
    # create temporary files with duplicate content
    d = tmp_path / "scan"
    d.mkdir()
    f1 = d / "a.txt"
    f2 = d / "b.txt"
    content = b"hello world"
    f1.write_bytes(content)
    f2.write_bytes(content)

    client = app.app.test_client()
    # find duplicates
    r = client.post("/api/duplicates", json={"paths": [str(d)], "min_size": 1})
    assert r.status_code == 200
    dup = r.get_json().get("duplicates")
    assert isinstance(dup, list) and len(dup) >= 1

    # generate heuristic suggestions
    r2 = client.post("/api/organise", json={"duplicates": dup})
    assert r2.status_code == 200
    suggestions = r2.get_json().get("suggestions")
    assert suggestions and isinstance(suggestions, list)

    # create preview op
    r3 = client.post("/api/organise/preview", json={"suggestions": suggestions})
    assert r3.status_code == 200
    op = r3.get_json().get("op")
    assert op and op.get("id")

    # execute with dry_run
    r4 = client.post(
        "/api/organise/execute",
        json={"op_id": op.get("id"), "dry_run": True},
    )
    assert r4.status_code == 200
    j = r4.get_json()
    assert j.get("dry_run") is True
    assert isinstance(j.get("preview"), list)
    assert "summary" in j

    # ensure files still exist on disk
    assert f1.exists()
    assert f2.exists()
