"""Build rich file contexts for LLM-driven analysis.

The current duplicate scanner is excellent for exact duplicates, but the
analysis flow needs richer filesystem metadata so the planner can reason about
semantic groupings, stale files, and safer re-organisation proposals.
"""

from __future__ import annotations

import hashlib
import importlib
import mimetypes
import os
import re
import time
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Callable, Dict, Iterable, List, Sequence
from xml.etree import ElementTree

try:
    xxhash = importlib.import_module("xxhash")
except Exception:  # pragma: no cover - optional dependency already used elsewhere
    xxhash = None

try:
    imagehash = importlib.import_module("imagehash")
except Exception:  # pragma: no cover - optional dependency for image similarity
    imagehash = None

try:
    pil_image = importlib.import_module("PIL.Image")
except Exception:  # pragma: no cover - optional dependency for image similarity
    pil_image = None

try:
    pypdf = importlib.import_module("pypdf")
except Exception:  # pragma: no cover - optional dependency for pdf text extraction
    pypdf = None

try:
    pytesseract = importlib.import_module("pytesseract")
except Exception:  # pragma: no cover - optional dependency for OCR
    pytesseract = None

try:
    pdf2image = importlib.import_module("pdf2image")
except Exception:  # pragma: no cover - optional dependency for OCR on scanned PDFs
    pdf2image = None

try:
    sentence_transformers = importlib.import_module("sentence_transformers")
except Exception:  # pragma: no cover - optional dependency for embeddings
    sentence_transformers = None

try:
    np = importlib.import_module("numpy")
except Exception:  # pragma: no cover - optional dependency for embeddings math
    np = None


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_VERSION_TOKEN_RE = re.compile(r"^(v?\d+(?:\.\d+)*|copy|final|draft|backup)$", re.I)

EXTENSION_GROUPS = {
    "images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".svg", ".bmp", ".tif", ".tiff"},
    "documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".pages", ".odt"},
    "spreadsheets": {".xls", ".xlsx", ".csv", ".numbers", ".ods"},
    "presentations": {".ppt", ".pptx", ".key"},
    "archives": {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".dmg", ".pkg"},
    "audio": {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"},
    "video": {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"},
    "code": {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yml", ".yaml", ".toml", ".ini", ".css", ".html", ".sh", ".go", ".rs", ".java", ".c", ".cpp"},
}

STALE_FILE_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}
STALE_SUFFIXES = {".tmp", ".temp", ".bak", ".old", ".orig", ".swp", ".pyc"}
STALE_DIR_MARKERS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".cache", "cache", "logs"}
TEXTUAL_GROUPS = {"documents", "spreadsheets", "presentations", "code"}
STOPWORDS = {
    "about",
    "after",
    "before",
    "could",
    "final",
    "from",
    "have",
    "into",
    "just",
    "more",
    "notes",
    "report",
    "that",
    "their",
    "there",
    "these",
    "this",
    "version",
    "with",
    "your",
}
DOCX_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_EMBEDDING_STATE = {"model": None, "disabled": False}
_EMBEDDING_CACHE: Dict[str, object] = {}


@dataclass
class FileContext:
    path: str
    name: str
    stem: str
    normalized_name: str
    extension: str
    extension_group: str
    size: int
    mtime: float
    age_days: float
    mime_type: str
    parent: str
    root: str
    depth: int
    path_tokens: List[str]
    sibling_count: int
    co_located_extensions: List[str]
    probable_stale_reasons: List[str]
    content_sample_kind: str
    content_signature: str
    content_terms: List[str]
    content_embedding_text: str
    near_duplicate_key: str
    near_duplicate_signals: List[str]
    near_duplicate_score: float

    def to_dict(self) -> Dict:
        return asdict(self)


def _tokenize(text: str) -> List[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]


def classify_extension(extension: str) -> str:
    ext = (extension or "").lower()
    for group, extensions in EXTENSION_GROUPS.items():
        if ext in extensions:
            return group
    return "other"


def _hash_bytes(data: bytes) -> str:
    if xxhash is not None:
        return xxhash.xxh64_hexdigest(data)
    return hashlib.sha1(data).hexdigest()[:16]


def _read_sample(path: str, size: int, head_bytes: int = 32768, tail_bytes: int = 8192) -> bytes:
    try:
        with open(path, "rb") as handle:
            if size <= head_bytes + tail_bytes:
                return handle.read(head_bytes + tail_bytes)
            head = handle.read(head_bytes)
            handle.seek(max(0, size - tail_bytes))
            tail = handle.read(tail_bytes)
            return head + b"\n" + tail
    except OSError:
        return b""


def _is_text_like(mime_type: str, extension_group: str) -> bool:
    mime = (mime_type or "").lower()
    if mime.startswith("text/"):
        return True
    if extension_group in TEXTUAL_GROUPS:
        return True
    return any(marker in mime for marker in ("json", "xml", "yaml", "javascript"))


def _extract_text_from_pdf(path: str) -> str:
    if pypdf is not None:
        try:
            reader = pypdf.PdfReader(path)
            text_parts: List[str] = []
            for page in reader.pages[:4]:
                page_text = page.extract_text() or ""
                if page_text:
                    text_parts.append(page_text)
                if sum(len(part) for part in text_parts) > 12000:
                    break
            if text_parts:
                return "\n".join(text_parts)
        except Exception:
            pass

    # Fallback for simple PDFs with plain-text stream sections.
    sample = _read_sample(path, os.path.getsize(path) if os.path.exists(path) else 0)
    if not sample:
        return ""
    decoded = sample.decode("latin-1", errors="ignore")
    text_chunks = re.findall(r"\(([^\)]{2,250})\)", decoded)
    if text_chunks:
        return " ".join(text_chunks)
    return decoded


def _ocr_text_from_image(path: str) -> str:
    if pil_image is None or pytesseract is None:
        return ""
    try:
        with pil_image.open(path) as image:
            text = pytesseract.image_to_string(image)
            return (text or "").strip()
    except Exception:
        return ""


def _ocr_text_from_pdf(path: str) -> str:
    if pdf2image is None or pytesseract is None:
        return ""
    try:
        pages = pdf2image.convert_from_path(path, first_page=1, last_page=2, dpi=200)
    except Exception:
        return ""

    text_parts: List[str] = []
    for page in pages:
        try:
            text = pytesseract.image_to_string(page)
        except Exception:
            text = ""
        if text and text.strip():
            text_parts.append(text.strip())
    return "\n".join(text_parts)


def _extract_text_from_docx(path: str) -> str:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            xml_payload = archive.read("word/document.xml")
    except Exception:
        return ""

    try:
        root = ElementTree.fromstring(xml_payload)
    except Exception:
        return ""

    texts: List[str] = []
    for node in root.iter(f"{DOCX_NS}t"):
        if node.text:
            texts.append(node.text)
    return " ".join(texts)


def _extract_image_signature(path: str) -> str:
    if imagehash is None or pil_image is None:
        return ""
    try:
        with pil_image.open(path) as img:
            return str(imagehash.phash(img, hash_size=8))
    except Exception:
        return ""


def _image_hash_similarity(left_signature: str, right_signature: str) -> float:
    if not left_signature or not right_signature:
        return 0.0

    if imagehash is not None:
        try:
            left_hash = imagehash.hex_to_hash(left_signature)
            right_hash = imagehash.hex_to_hash(right_signature)
            max_bits = int(left_hash.hash.size)
            distance = left_hash - right_hash
            return max(0.0, min(1.0, 1.0 - (distance / max_bits)))
        except Exception:
            pass

    try:
        left_int = int(left_signature, 16)
        right_int = int(right_signature, 16)
        width = max(len(left_signature), len(right_signature)) * 4
        differing_bits = (left_int ^ right_int).bit_count()
        return max(0.0, min(1.0, 1.0 - (differing_bits / max(width, 1))))
    except Exception:
        return 0.0


def _terms_and_signature(text: str, fallback_sample: bytes) -> tuple[str, List[str]]:
    tokens = [
        token
        for token in _tokenize(text)
        if len(token) >= 3 and token not in STOPWORDS and not _VERSION_TOKEN_RE.match(token)
    ]
    if not tokens:
        return _hash_bytes(fallback_sample), []
    counts = Counter(tokens)
    top_terms = sorted(token for token, _count in counts.most_common(12))
    signature_source = " ".join(tokens[:512]).encode("utf-8", errors="ignore")
    return _hash_bytes(signature_source), top_terms


def _text_for_embedding(text: str, terms: Sequence[str]) -> str:
    raw = (text or "").strip()
    if raw:
        compact = " ".join(raw.split())
        return compact[:4000]
    if terms:
        return " ".join(terms)
    return ""


def _load_embedding_model():
    if _EMBEDDING_STATE["disabled"]:
        return None
    if _EMBEDDING_STATE["model"] is not None:
        return _EMBEDDING_STATE["model"]
    if sentence_transformers is None:
        _EMBEDDING_STATE["disabled"] = True
        return None
    try:
        model_name = os.getenv("DISK_ORGANISER_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _EMBEDDING_STATE["model"] = sentence_transformers.SentenceTransformer(model_name)
        return _EMBEDDING_STATE["model"]
    except Exception:
        _EMBEDDING_STATE["disabled"] = True
        return None


def _embedding_vector(text: str):
    if not text:
        return None
    model = _load_embedding_model()
    if model is None or np is None:
        return None
    cached = _EMBEDDING_CACHE.get(text)
    if cached is not None:
        return cached
    try:
        vector = model.encode([text], normalize_embeddings=True)[0]
        vector_np = np.array(vector, dtype=float)
        _EMBEDDING_CACHE[text] = vector_np
        return vector_np
    except Exception:
        return None


def _embedding_similarity(left_text: str, right_text: str) -> float:
    left_vec = _embedding_vector(left_text)
    right_vec = _embedding_vector(right_text)
    if left_vec is None or right_vec is None or np is None:
        return 0.0
    try:
        return float(np.dot(left_vec, right_vec))
    except Exception:
        return 0.0


def _extract_content_features(
    path: str,
    extension: str,
    mime_type: str,
    extension_group: str,
    size: int,
) -> tuple[str, str, List[str], str]:
    sample = _read_sample(path, size)
    if not sample:
        return "unavailable", "", [], ""

    ext = (extension or "").lower()
    if extension_group == "images":
        image_signature = _extract_image_signature(path)
        ocr_text = _ocr_text_from_image(path)
        ocr_signature, ocr_terms = _terms_and_signature(ocr_text, sample)
        if image_signature:
            if ocr_terms:
                return "image-phash-ocr", image_signature, ocr_terms, _text_for_embedding(ocr_text, ocr_terms)
            return "image-phash", image_signature, [], ""
        if ocr_terms:
            return "image-ocr", ocr_signature, ocr_terms, _text_for_embedding(ocr_text, ocr_terms)
        return "binary", _hash_bytes(sample), [], ""

    if ext == ".pdf":
        pdf_text = _extract_text_from_pdf(path)
        used_ocr = False
        if len(_tokenize(pdf_text)) < 8:
            ocr_pdf_text = _ocr_text_from_pdf(path)
            if len(_tokenize(ocr_pdf_text)) >= len(_tokenize(pdf_text)):
                pdf_text = ocr_pdf_text
                used_ocr = True
        signature, terms = _terms_and_signature(pdf_text, sample)
        kind = "pdf-ocr" if used_ocr and terms else "pdf-text"
        return kind, signature, terms, _text_for_embedding(pdf_text, terms)

    if ext == ".docx":
        docx_text = _extract_text_from_docx(path)
        signature, terms = _terms_and_signature(docx_text, sample)
        return "docx-text", signature, terms, _text_for_embedding(docx_text, terms)

    if _is_text_like(mime_type, extension_group):
        decoded = sample.decode("utf-8", errors="ignore")
        signature, terms = _terms_and_signature(decoded, sample)
        return "text", signature, terms, _text_for_embedding(decoded, terms)

    return "binary", _hash_bytes(sample), [], ""


def _token_similarity(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = {item for item in left if item}
    right_set = {item for item in right if item}
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def _size_similarity(left_size: int, right_size: int) -> float:
    if left_size <= 0 or right_size <= 0:
        return 0.0
    return min(left_size, right_size) / max(left_size, right_size)


def _component_key(extension_group: str, paths: Sequence[str]) -> str:
    seed = "|".join(sorted(paths)).encode("utf-8", errors="ignore")
    return f"content:{extension_group}:{_hash_bytes(seed)[:12]}"


def _candidate_bucket_keys(item: FileContext) -> set[str]:
    keys = {
        f"name:{item.extension_group}:{item.normalized_name}:{item.extension}",
        f"ext:{item.extension_group}:{item.extension}",
    }
    for term in item.content_terms[:3]:
        keys.add(f"term:{item.extension_group}:{term}")
    return keys


def _pair_metrics(left: FileContext, right: FileContext) -> tuple[float, float, float, float]:
    name_similarity = _token_similarity(left.normalized_name.split("-"), right.normalized_name.split("-"))
    size_similarity = _size_similarity(left.size, right.size)

    if left.content_sample_kind.startswith("image-phash") and right.content_sample_kind.startswith("image-phash"):
        image_similarity = _image_hash_similarity(left.content_signature, right.content_signature)
        score = (0.75 * image_similarity) + (0.15 * name_similarity) + (0.10 * size_similarity)
        return score, image_similarity, name_similarity, size_similarity

    content_similarity = _token_similarity(left.content_terms, right.content_terms)

    if left.content_signature and left.content_signature == right.content_signature and size_similarity >= 0.9:
        return 1.0, 1.0, name_similarity, size_similarity

    if left.content_sample_kind == right.content_sample_kind == "text":
        score = (0.55 * content_similarity) + (0.25 * name_similarity) + (0.2 * size_similarity)
        return score, content_similarity, name_similarity, size_similarity

    score = (0.45 * name_similarity) + (0.35 * size_similarity)
    return score, content_similarity, name_similarity, size_similarity


def _build_near_duplicate_clusters(contexts: Sequence[FileContext]) -> Dict[int, Dict]:
    parent = list(range(len(contexts)))
    union_reasons: List[tuple[int, int, List[str], float]] = []

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int, reasons: List[str], score: float):
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            union_reasons.append((left, right, reasons, score))
            return
        parent[right_root] = left_root
        union_reasons.append((left, right, reasons, score))

    buckets: Dict[str, List[int]] = defaultdict(list)
    for index, context in enumerate(contexts):
        for key in _candidate_bucket_keys(context):
            buckets[key].append(index)

    seen_pairs = set()
    for indexes in buckets.values():
        if len(indexes) < 2:
            continue
        for offset, left_index in enumerate(indexes):
            left = contexts[left_index]
            for right_index in indexes[offset + 1 :]:
                pair = tuple(sorted((left_index, right_index)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                right = contexts[right_index]
                if left.extension_group != right.extension_group:
                    continue
                score, content_similarity, name_similarity, size_similarity = _pair_metrics(left, right)
                reasons: List[str] = []
                if (
                    not left.content_sample_kind.startswith("image-phash")
                    and left.content_signature
                    and left.content_signature == right.content_signature
                    and size_similarity >= 0.9
                ):
                    reasons.append("matching-content-signature")
                if left.content_sample_kind.startswith("image-phash") and right.content_sample_kind.startswith("image-phash"):
                    if content_similarity >= 0.80:
                        reasons.append("image-phash-similarity")
                elif content_similarity >= 0.45:
                    reasons.append("content-overlap")
                embedding_similarity = 0.0
                if not reasons and left.content_embedding_text and right.content_embedding_text:
                    embedding_similarity = _embedding_similarity(
                        left.content_embedding_text,
                        right.content_embedding_text,
                    )
                    if embedding_similarity >= 0.90 and size_similarity >= 0.4:
                        reasons.append("embedding-similarity")
                if name_similarity >= 0.4:
                    reasons.append("name-similarity")
                if size_similarity >= 0.75:
                    reasons.append("similar-size")
                should_cluster = (
                    "matching-content-signature" in reasons
                    or "image-phash-similarity" in reasons
                    or "embedding-similarity" in reasons
                    or (content_similarity >= 0.55 and size_similarity >= 0.55)
                    or (name_similarity >= 0.8 and size_similarity >= 0.45)
                    or score >= 0.72
                )
                if should_cluster and reasons:
                    if embedding_similarity > 0:
                        score = max(score, embedding_similarity)
                    union(left_index, right_index, reasons, score)

    components: Dict[int, List[int]] = defaultdict(list)
    for index in range(len(contexts)):
        components[find(index)].append(index)

    component_reasons: Dict[int, set[str]] = defaultdict(set)
    component_scores: Dict[int, float] = defaultdict(float)
    for left, right, reasons, score in union_reasons:
        root = find(left)
        if find(right) != root:
            continue
        component_reasons[root].update(reasons)
        component_scores[root] = max(component_scores[root], score)

    results: Dict[int, Dict] = {}
    for root, indexes in components.items():
        if len(indexes) <= 1:
            continue
        cluster_paths = [contexts[index].path for index in indexes]
        key = _component_key(contexts[indexes[0]].extension_group, cluster_paths)
        signals = sorted(component_reasons.get(root) or {"name-similarity"})
        score = round(component_scores.get(root, 0.72), 3)
        for index in indexes:
            results[index] = {"key": key, "signals": signals, "score": score}
    return results


def _normalized_name(stem: str) -> str:
    tokens = [tok for tok in _tokenize(stem) if not _VERSION_TOKEN_RE.match(tok)]
    return "-".join(tokens) or stem.lower()


def detect_stale_reasons(path: str, size: int, age_days: float) -> List[str]:
    reasons: List[str] = []
    basename = os.path.basename(path).lower()
    extension = os.path.splitext(basename)[1]
    path_parts = [part.lower() for part in os.path.normpath(path).split(os.sep) if part]

    if basename in STALE_FILE_NAMES:
        reasons.append("system-metadata")
    if extension in STALE_SUFFIXES:
        reasons.append("temporary-or-backup-suffix")
    if any(part in STALE_DIR_MARKERS for part in path_parts):
        reasons.append("cache-or-build-artifact")
    if size == 0:
        reasons.append("zero-byte-file")
    if extension in {".dmg", ".pkg", ".iso"} and age_days > 30:
        reasons.append("old-installer-image")
    if any(part in {"downloads", "desktop"} for part in path_parts) and basename.endswith(" copy"):
        reasons.append("likely-manual-copy")
    if "/library/caches/" in path.lower() or "/.cache/" in path.lower():
        reasons.append("cache-location")

    deduped: List[str] = []
    seen = set()
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            deduped.append(reason)
    return deduped


def _iter_files(paths: Sequence[str]) -> Iterable[tuple[str, str, os.stat_result]]:
    for root in paths:
        if not os.path.exists(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", ".venv", "venv"}]
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                try:
                    stat_result = os.stat(full_path)
                except (OSError, PermissionError):
                    continue
                yield root, full_path, stat_result


def build_context(
    paths: Sequence[str],
    min_size: int = 1,
    max_files: int | None = None,
    progress_callback: Callable[[Dict], None] | None = None,
) -> List[Dict]:
    now = time.time()
    raw_files: List[tuple[str, str, os.stat_result]] = []
    per_parent_extensions: Dict[str, Counter] = defaultdict(Counter)
    sibling_counts: Counter = Counter()

    for index, item in enumerate(_iter_files(paths), start=1):
        root, full_path, stat_result = item
        if stat_result.st_size < min_size:
            continue
        raw_files.append(item)
        parent = os.path.dirname(full_path)
        extension = os.path.splitext(full_path)[1].lower()
        per_parent_extensions[parent][extension or "<none>"] += 1
        sibling_counts[parent] += 1
        if progress_callback and index % 100 == 0:
            progress_callback({"status": "scanning", "processed": index})
        if max_files is not None and len(raw_files) >= max_files:
            break

    contexts: List[FileContext] = []
    base_key_counts: Counter = Counter()
    for root, full_path, stat_result in raw_files:
        name = os.path.basename(full_path)
        stem, extension = os.path.splitext(name)
        normalized = _normalized_name(stem)
        age_days = max(0.0, (now - stat_result.st_mtime) / 86400.0)
        mime_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
        parent = os.path.dirname(full_path)
        extension_group = classify_extension(extension)
        tokens = _tokenize(os.path.relpath(full_path, root))
        content_sample_kind, content_signature, content_terms, content_embedding_text = _extract_content_features(
            full_path,
            extension.lower(),
            mime_type,
            extension_group,
            int(stat_result.st_size),
        )
        near_duplicate_key = f"{normalized}:{extension_group}:{extension.lower()}"
        base_key_counts[near_duplicate_key] += 1
        co_located = [ext for ext, _count in per_parent_extensions[parent].most_common(5)]
        context = FileContext(
            path=os.path.abspath(full_path),
            name=name,
            stem=stem,
            normalized_name=normalized,
            extension=extension.lower(),
            extension_group=extension_group,
            size=int(stat_result.st_size),
            mtime=float(stat_result.st_mtime),
            age_days=round(age_days, 2),
            mime_type=mime_type,
            parent=os.path.abspath(parent),
            root=os.path.abspath(root),
            depth=max(0, len(os.path.relpath(parent, root).split(os.sep))) if os.path.abspath(parent) != os.path.abspath(root) else 0,
            path_tokens=tokens,
            sibling_count=int(sibling_counts[parent]),
            co_located_extensions=co_located,
            probable_stale_reasons=detect_stale_reasons(full_path, int(stat_result.st_size), age_days),
            content_sample_kind=content_sample_kind,
            content_signature=content_signature,
            content_terms=content_terms,
            content_embedding_text=content_embedding_text,
            near_duplicate_key=near_duplicate_key,
            near_duplicate_signals=[],
            near_duplicate_score=0.0,
        )
        contexts.append(context)

    cluster_overrides = _build_near_duplicate_clusters(contexts)
    out: List[Dict] = []
    final_key_counts: Counter = Counter()
    for index, context in enumerate(contexts):
        key = cluster_overrides.get(index, {}).get("key") or context.near_duplicate_key
        final_key_counts[key] += 1

    for index, context in enumerate(contexts):
        payload = context.to_dict()
        override = cluster_overrides.get(index)
        if override:
            payload["near_duplicate_key"] = override["key"]
            payload["near_duplicate_signals"] = override["signals"]
            payload["near_duplicate_score"] = override["score"]
        elif base_key_counts[context.near_duplicate_key] > 1:
            payload["near_duplicate_signals"] = ["name-similarity"]
            payload["near_duplicate_score"] = 0.65
        payload["near_duplicate_group_size"] = final_key_counts[payload["near_duplicate_key"]]
        out.append(payload)
    return out


def summarize_contexts(contexts: Sequence[Dict]) -> Dict:
    total_size = sum(int(item.get("size") or 0) for item in contexts)
    extension_groups = Counter(item.get("extension_group") or "other" for item in contexts)
    stale_candidates = sum(1 for item in contexts if item.get("probable_stale_reasons"))
    near_duplicate_clusters = Counter(item.get("near_duplicate_key") for item in contexts if item.get("near_duplicate_key"))
    return {
        "file_count": len(contexts),
        "total_bytes": total_size,
        "extension_groups": dict(extension_groups.most_common()),
        "stale_candidates": stale_candidates,
        "near_duplicate_clusters": sum(1 for _key, count in near_duplicate_clusters.items() if count > 1),
    }


def summarise_folders_for_visualisation(contexts: Sequence[Dict]) -> Dict[str, Dict]:
    folder_stats: Dict[str, Dict] = {}
    for item in contexts:
        parent = item.get("parent")
        if not parent:
            continue
        info = folder_stats.setdefault(parent, {"bytes": 0, "files": 0, "stale": 0, "semantic_groups": set()})
        info["bytes"] += int(item.get("size") or 0)
        info["files"] += 1
        if item.get("probable_stale_reasons"):
            info["stale"] += 1
        key = item.get("near_duplicate_key")
        if key and int(item.get("near_duplicate_group_size") or 0) > 1:
            info["semantic_groups"].add(key)
    for info in folder_stats.values():
        info["semantic_groups"] = len(info["semantic_groups"])
    return folder_stats