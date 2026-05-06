import os
import sys
import zipfile

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from backend.context_builder import build_context, summarize_contexts  # noqa: E402


def test_build_context_marks_stale_and_semantic_clusters(tmp_path):
    root = tmp_path / "drive"
    docs = root / "Docs"
    downloads = root / "Downloads"
    cache = root / "Library" / "Caches"
    docs.mkdir(parents=True)
    downloads.mkdir(parents=True)
    cache.mkdir(parents=True)

    (docs / "Project Plan v1.pdf").write_text("alpha", encoding="utf-8")
    (downloads / "Project Plan final.pdf").write_text("beta", encoding="utf-8")
    (cache / ".DS_Store").write_text("cache", encoding="utf-8")

    contexts = build_context([str(root)], min_size=0)
    assert len(contexts) == 3

    stale = [item for item in contexts if item["name"] == ".DS_Store"][0]
    assert "system-metadata" in stale["probable_stale_reasons"]

    project_files = [item for item in contexts if item["normalized_name"].startswith("project-plan")]
    assert len(project_files) == 2
    assert project_files[0]["near_duplicate_key"] == project_files[1]["near_duplicate_key"]
    assert project_files[0]["content_sample_kind"] in {"text", "pdf-text"}
    assert "name-similarity" in project_files[0]["near_duplicate_signals"] or "content-overlap" in project_files[0]["near_duplicate_signals"]

    summary = summarize_contexts(contexts)
    assert summary["stale_candidates"] == 1
    assert summary["near_duplicate_clusters"] >= 1


def test_build_context_uses_content_overlap_for_near_duplicates(tmp_path):
    root = tmp_path / "drive"
    drafts = root / "Drafts"
    archive = root / "Archive"
    drafts.mkdir(parents=True)
    archive.mkdir(parents=True)

    (drafts / "meeting-notes.txt").write_text(
        "Quarterly budget planning roadmap staffing timeline launch blockers and follow up owners.",
        encoding="utf-8",
    )
    (archive / "roadmap-summary.txt").write_text(
        "Budget planning roadmap staffing timeline launch blockers and follow up owners for the quarter.",
        encoding="utf-8",
    )

    contexts = build_context([str(root)], min_size=0)
    assert len(contexts) == 2
    assert contexts[0]["near_duplicate_key"] == contexts[1]["near_duplicate_key"]
    assert "content-overlap" in contexts[0]["near_duplicate_signals"]
    assert contexts[0]["near_duplicate_group_size"] == 2


def test_build_context_extracts_docx_and_pdf_terms(tmp_path):
    root = tmp_path / "docs"
    root.mkdir(parents=True)

    docx_path = root / "plan.docx"
    with zipfile.ZipFile(docx_path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            """
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body>
                <w:p><w:r><w:t>Roadmap staffing timeline blockers and budget planning.</w:t></w:r></w:p>
              </w:body>
            </w:document>
            """,
        )

    pdf_path = root / "summary.pdf"
    pdf_path.write_bytes(
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R>>endobj\n"
        b"4 0 obj<</Length 80>>stream\nBT /F1 12 Tf 72 120 Td (Budget planning timeline blockers summary) Tj ET\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000115 00000 n \n0000000200 00000 n \n"
        b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n320\n%%EOF\n"
    )

    contexts = build_context([str(root)], min_size=0)
    by_name = {item["name"]: item for item in contexts}

    assert by_name["plan.docx"]["content_sample_kind"] == "docx-text"
    assert "roadmap" in by_name["plan.docx"]["content_terms"]
    assert by_name["summary.pdf"]["content_sample_kind"] == "pdf-text"
    assert "budget" in by_name["summary.pdf"]["content_terms"]


def test_build_context_uses_image_perceptual_hash_for_near_duplicates(tmp_path):
    pil_image = pytest.importorskip("PIL.Image")
    pytest.importorskip("imagehash")

    root = tmp_path / "images"
    root.mkdir(parents=True)

    image_one = root / "scene_a.png"
    image_two = root / "scene_b.png"

    img = pil_image.new("RGB", (64, 64), color=(245, 245, 245))
    for x in range(16, 48):
        for y in range(18, 46):
            img.putpixel((x, y), (30, 70, 140))
    img.save(image_one)

    variant = pil_image.open(image_one).copy()
    variant.save(image_two)

    contexts = build_context([str(root)], min_size=0)
    assert len(contexts) == 2
    assert contexts[0]["content_sample_kind"] == "image-phash"
    assert contexts[0]["near_duplicate_key"] == contexts[1]["near_duplicate_key"]
    assert any(
        signal in {"image-phash-similarity", "matching-content-signature"}
        for signal in contexts[0]["near_duplicate_signals"]
    )


def test_build_context_uses_ocr_path_for_scanned_pdf(monkeypatch, tmp_path):
    root = tmp_path / "scanned-pdf"
    root.mkdir(parents=True)
    scanned_pdf = root / "invoice-scan.pdf"
    scanned_pdf.write_bytes(b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF\n")

    monkeypatch.setattr("backend.context_builder._extract_text_from_pdf", lambda _path: "")
    monkeypatch.setattr(
        "backend.context_builder._ocr_text_from_pdf",
        lambda _path: "Invoice total amount due customer payment reference",
    )

    contexts = build_context([str(root)], min_size=0)
    assert len(contexts) == 1
    assert contexts[0]["content_sample_kind"] == "pdf-ocr"
    assert "invoice" in contexts[0]["content_terms"]


def test_build_context_uses_embedding_similarity_for_hard_cases(monkeypatch, tmp_path):
    root = tmp_path / "embedding"
    one = root / "Alpha"
    two = root / "Beta"
    one.mkdir(parents=True)
    two.mkdir(parents=True)

    (one / "brief-a.txt").write_text("quokka amber horizon", encoding="utf-8")
    (two / "brief-b.txt").write_text("nebula cobalt archive", encoding="utf-8")

    monkeypatch.setattr(
        "backend.context_builder._embedding_similarity",
        lambda left, right: 0.95 if left and right else 0.0,
    )

    contexts = build_context([str(root)], min_size=0)
    assert len(contexts) == 2
    assert contexts[0]["near_duplicate_key"] == contexts[1]["near_duplicate_key"]
    assert "embedding-similarity" in contexts[0]["near_duplicate_signals"]