import importlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

app = importlib.import_module("backend.app")


def test_analyse_reason_preview_and_chat_refinement(tmp_path):
    root = tmp_path / "analysis"
    docs = root / "Documents"
    downloads = root / "Downloads"
    cache = root / "Library" / "Caches"
    docs.mkdir(parents=True)
    downloads.mkdir(parents=True)
    cache.mkdir(parents=True)

    (docs / "Project Plan v1.pdf").write_text("proposal", encoding="utf-8")
    (downloads / "Project Plan final.pdf").write_text("proposal-final", encoding="utf-8")
    (cache / ".DS_Store").write_text("cache", encoding="utf-8")

    client = app.app.test_client()
    response = client.post("/api/analyse/reason", json={"paths": [str(root)]})
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["op"]["id"]
    assert payload["summary"]["actions"] >= 1
    assert payload["backup_status"] is not None
    assert "analysis_capabilities" in payload
    assert isinstance(payload["analysis_capabilities"], dict)
    assert "ocr" in payload["analysis_capabilities"]
    assert "embeddings" in payload["analysis_capabilities"]
    assert any(action["action"] in {"delete_stale", "move", "create_symlink"}
               for action in payload["actions"])

    preview_response = client.get(f"/api/ops/{payload['op']['id']}/preview")
    assert preview_response.status_code == 200
    preview = preview_response.get_json()
    assert preview["grouped"]

    chat_response = client.post(
        "/api/chat",
        json={"op_id": payload["op"]["id"], "message": "delete nothing from this proposal"},
    )
    assert chat_response.status_code == 200
    refined = chat_response.get_json()
    assert all(action["action"] != "delete_stale" for action in refined["actions"])


def test_analyse_reason_groups_content_similar_files_with_different_names(tmp_path):
    root = tmp_path / "analysis"
    drafts = root / "Drafts"
    references = root / "References"
    drafts.mkdir(parents=True)
    references.mkdir(parents=True)

    (drafts / "meeting-notes.txt").write_text(
        "Quarterly budget planning roadmap staffing timeline launch blockers and follow up owners.",
        encoding="utf-8",
    )
    (references / "roadmap-summary.txt").write_text(
        "Budget planning roadmap staffing timeline launch blockers and follow up owners for the quarter.",
        encoding="utf-8",
    )

    client = app.app.test_client()
    response = client.post("/api/analyse/reason", json={"paths": [str(root)]})
    assert response.status_code == 200
    payload = response.get_json()

    semantic_actions = [action for action in payload["actions"] if action["action"] == "move"]
    assert semantic_actions
    assert any("content" in (action.get("reason") or "").lower() for action in semantic_actions)


def test_analyse_reason_capabilities_disabled_branch(monkeypatch, tmp_path):
    root = tmp_path / "analysis"
    root.mkdir(parents=True)
    (root / "a.txt").write_text("alpha", encoding="utf-8")

    monkeypatch.setattr(
        app,
        "get_runtime_capabilities",
        lambda: {
            "ocr": {
                "available": False,
                "image": False,
                "pdf": False,
                "missing": ["pytesseract", "pdf2image", "Pillow"],
            },
            "embeddings": {
                "available": False,
                "disabled": True,
                "model": "all-MiniLM-L6-v2",
                "missing": ["sentence-transformers", "numpy"],
            },
        },
    )

    client = app.app.test_client()
    response = client.post("/api/analyse/reason", json={"paths": [str(root)]})
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["analysis_capabilities"]["ocr"]["available"] is False
    assert payload["analysis_capabilities"]["ocr"]["missing"] == [
        "pytesseract",
        "pdf2image",
        "Pillow",
    ]
    assert payload["analysis_capabilities"]["embeddings"]["available"] is False
    assert payload["analysis_capabilities"]["embeddings"]["disabled"] is True
    assert payload["analysis_capabilities"]["embeddings"]["missing"] == [
        "sentence-transformers",
        "numpy",
    ]


def test_analyse_reason_capabilities_enabled_branch(monkeypatch, tmp_path):
    root = tmp_path / "analysis"
    root.mkdir(parents=True)
    (root / "a.txt").write_text("alpha", encoding="utf-8")

    monkeypatch.setattr(
        app,
        "get_runtime_capabilities",
        lambda: {
            "ocr": {
                "available": True,
                "image": True,
                "pdf": True,
                "missing": [],
            },
            "embeddings": {
                "available": True,
                "disabled": False,
                "model": "all-MiniLM-L6-v2",
                "missing": [],
            },
        },
    )

    client = app.app.test_client()
    response = client.post("/api/analyse/reason", json={"paths": [str(root)]})
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["analysis_capabilities"]["ocr"]["available"] is True
    assert payload["analysis_capabilities"]["ocr"]["missing"] == []
    assert payload["analysis_capabilities"]["embeddings"]["available"] is True
    assert payload["analysis_capabilities"]["embeddings"]["disabled"] is False
    assert payload["analysis_capabilities"]["embeddings"]["missing"] == []
