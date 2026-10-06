"""Deterministic analysis of observations only; no filesystem or network access."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import PurePosixPath
from datetime import datetime, timedelta

from backend.disk_model import stable_id

MAX_FINDINGS = 400
MAX_RELATIONSHIPS = 2000
_ROLE_NAMES = {"archive": {"archive", "archives", "backup", "backups"},
               "inbox": {"inbox", "downloads", "incoming", "unsorted"},
               "cache": {"cache", "caches", ".cache", "node_modules", "__pycache__"}}
_PROJECT_MARKERS = {".git", "pyproject.toml", "package.json", "Cargo.toml", "CMakeLists.txt", "Makefile"}
_VERSION = re.compile(r"(?:[ _.-]+(?:v\d+(?:[._]\d+)*|rev\d+|draft|final|copy|backup|export|render))+$", re.I)
_TYPES = {"documents": {".pdf", ".txt", ".md", ".docx", ".odt"},
          "images": {".png", ".jpg", ".jpeg", ".tiff", ".svg"},
          "video": {".mp4", ".mov", ".mkv"}, "audio": {".wav", ".mp3", ".flac"},
          "archives": {".zip", ".tar", ".gz", ".7z"},
          "code": {".py", ".js", ".ts", ".rs", ".c", ".cpp"},
          "creative_projects": {".blend", ".psd", ".aep"}}


def _category(path):
    suffix = PurePosixPath(path).suffix.lower()
    return next((name for name, extensions in _TYPES.items() if suffix in extensions), "other")


def analyse_inventory(model: dict) -> dict:
    """Return evidence, conservative relationships and informational alternatives.

    All sizes are logical observations or stat allocation. There is no physical
    recovery estimate, content-derived semantics, disposal decision, or authority.
    """
    entries = sorted(model["entries"], key=lambda e: (e["root_id"], e["relative_path"]))
    by_id = {e["id"]: e for e in entries}
    observed_files = [e for e in entries if e["kind"] == "file" and e["status"] == "observed"]
    evidence, findings, relationships, directories, alternatives = [], [], [], [], []
    counts = {"findings_omitted": 0, "relationships_omitted": 0}

    def fact(kind, members, observations):
        item = {"id": stable_id("evidence", kind, members, observations), "kind": kind,
                "member_ids": members, "observations": observations, "confidence": "observed"}
        evidence.append(item)
        return item["id"]

    def finding(kind, members, evidence_ids, title, confidence, uncertainties, counter=None):
        if len(findings) >= MAX_FINDINGS:
            counts["findings_omitted"] += 1
            return
        findings.append({"id": stable_id("finding", kind, members), "kind": kind, "title": title,
                         "member_ids": members, "evidence_ids": evidence_ids, "confidence": confidence,
                         "uncertainties": uncertainties, "counter_evidence": counter or []})

    def relationship(kind, members, evidence_ids, confidence, uncertainties):
        if len(relationships) >= MAX_RELATIONSHIPS:
            counts["relationships_omitted"] += 1
            return
        relationships.append({"id": stable_id("relationship", kind, members), "kind": kind,
                              "member_ids": members, "evidence_ids": evidence_ids, "confidence": confidence,
                              "uncertainties": uncertainties})

    objects = defaultdict(list)
    hashes = defaultdict(list)
    families = defaultdict(list)
    categories = defaultdict(lambda: {"entry_count": 0, "logical_bytes": 0})
    for entry in observed_files:
        if entry["object_id"]:
            objects[entry["object_id"]].append(entry)
        if entry["hash"]["status"] == "verified":
            hashes[(entry["logical_bytes"], entry["hash"]["algorithm"], entry["hash"]["value"])].append(entry)
        filename = PurePosixPath(entry["relative_path"])
        stem = _VERSION.sub("", filename.stem).casefold()
        # Restrict name hypotheses to the same immediate directory and suffix.
        # Broad cross-folder/topic matches need a future user-reviewed model.
        if stem:
            families[(entry["root_id"], str(filename.parent), stem, filename.suffix.casefold())].append(entry)
        category = categories[_category(entry["relative_path"])]
        category["entry_count"] += 1
        category["logical_bytes"] += entry["logical_bytes"]

    for object_id, group in sorted(objects.items()):
        if len(group) < 2:
            continue
        members = [e["id"] for e in group]
        eid = fact("same_observed_file_object", members,
                   {"object_id": object_id, "observed_paths": len(group),
                    "reported_link_count": sorted({e["link_count"] for e in group})})
        relationship("hard_link_paths", members, [eid], "observed",
                     ["Inode identity is only an observation; it is not permanent identity.",
                      "Unobserved hard links may exist outside selected roots."])

    for (size, algorithm, digest), group in sorted(hashes.items()):
        # Paths to one object are aliases, not independent duplicate storage.
        identities = {e["object_id"] for e in group if e["object_id"]}
        unknown_identity = any(e["object_id"] is None for e in group)
        if len(group) < 2 or (not unknown_identity and len(identities) < 2):
            continue
        members = [e["id"] for e in group]
        eid = fact("full_content_hash_match", members,
                   {"algorithm": algorithm, "digest": digest, "logical_bytes_each": size,
                    "distinct_observed_objects": None if unknown_identity else len(identities),
                    "verified_in_this_scan": True})
        uncertainty = ["Byte-identical observations do not establish which copy is authoritative or safe to delete.",
                       "Content can change after hashing; shared physical extents are unknown."]
        kind = "content_match_identity_unknown" if unknown_identity else "exact_content_match"
        if unknown_identity:
            uncertainty.append("Missing object identities prevent distinguishing copies from hard-link aliases.")
        title = ("Matching full-file hashes; distinct file objects unknown" if unknown_identity else
                 "Matching full-file hashes across distinct objects")
        relationship(kind, members, [eid], "observed", uncertainty)
        finding(kind, members, [eid], title, "observed", uncertainty)

    for (_, _, stem, _), group in sorted(families.items()):
        if len(group) < 2 or not any(_VERSION.search(PurePosixPath(e["relative_path"]).stem) for e in group):
            continue
        members = [e["id"] for e in group]
        eid = fact("name_family_pattern", members,
                   {"normalised_stem": stem, "same_parent_and_extension": True,
                    "filenames": [PurePosixPath(e["relative_path"]).name for e in group]})
        uncertainty = ["Related names do not prove version lineage, quality, completeness or intent.",
                       "The latest modification time does not identify the preferred version."]
        relationship("version_like_names", members, [eid], "hypothesis", uncertainty)
        finding("version_like_names", members, [eid], "Names suggest a possible version or export family",
                "hypothesis", uncertainty)

    children = defaultdict(list)
    directory_totals = {}
    directory_gaps = defaultdict(set)
    for exclusion in model["scan"]["exclusions"]:
        directory_gaps[exclusion["entry_id"]].add(exclusion["reason"])
    for entry in entries:
        children[entry["parent_id"]].append(entry)
        if entry["kind"] == "directory":
            directory_totals[entry["id"]] = {"logical_bytes": 0, "observed_files": 0, "uncertain_entries": 0}
            if entry["status"] != "observed":
                directory_gaps[entry["id"]].add("directory_" + entry["status"])
            if model["scan"]["coverage"].get("stop_reason"):
                directory_gaps[entry["id"]].add("scan_interrupted")
    for entry in entries:
        totals = directory_totals.get(entry["parent_id"])
        if totals is not None:
            if entry["status"] != "observed":
                totals["uncertain_entries"] += 1
                directory_gaps[entry["parent_id"]].add("descendant_not_observed")
            elif entry["kind"] == "file":
                totals["logical_bytes"] += entry["logical_bytes"]
                totals["observed_files"] += 1
    ordered_dirs = sorted((e for e in entries if e["kind"] == "directory"),
                          key=lambda e: (-e["relative_path"].count("/"), e["relative_path"] == ".", e["id"]))
    # Deeper child totals accumulate once per directory, avoiding pairwise tree expansion.
    for entry in ordered_dirs:
        totals = directory_totals[entry["id"]]
        parent = directory_totals.get(entry["parent_id"])
        if parent is not None:
            for key, value in totals.items():
                parent[key] += value
            if directory_gaps[entry["id"]]:
                directory_gaps[entry["parent_id"]].add("descendant_coverage_incomplete")
    for entry in sorted(ordered_dirs, key=lambda e: e["id"]):
        direct = children[entry["id"]]
        names = {PurePosixPath(e["relative_path"]).name for e in direct}
        basename = PurePosixPath(entry["relative_path"]).name.casefold()
        hypotheses = []
        if entry["status"] == "observed":
            for role, markers in _ROLE_NAMES.items():
                if basename in markers:
                    eid = fact("directory_name", [entry["id"]], {"name": basename, "matched_role_label": role})
                    hypotheses.append({"role": role, "confidence": "hypothesis", "evidence_ids": [eid]})
            markers = sorted(names & _PROJECT_MARKERS)
            if markers:
                marker_ids = [e["id"] for e in direct if PurePosixPath(e["relative_path"]).name in markers]
                eid = fact("project_marker_names", [entry["id"], *marker_ids], {"marker_names": markers})
                hypotheses.append({"role": "project", "confidence": "hypothesis", "evidence_ids": [eid]})
        item = {"entry_id": entry["id"], "direct_member_ids": [e["id"] for e in direct],
                **directory_totals[entry["id"]], "role_hypotheses": hypotheses,
                "coverage": {"complete": not bool(directory_gaps[entry["id"]]),
                             "reasons": sorted(directory_gaps[entry["id"]])},
                "confidence": "hypothesis" if hypotheses else "unknown",
                "uncertainties": ["Directory names and marker names do not prove purpose or current activity.",
                                  "Logical totals count paths, including multiple hard links.",
                                  "Zero observed bytes in an incomplete subtree does not establish emptiness."]}
        directories.append(item)
        if hypotheses:
            finding("directory_role", [entry["id"]], [eid for h in hypotheses for eid in h["evidence_ids"]],
                    "Possible directory role: " + ", ".join(h["role"] for h in hypotheses),
                    "hypothesis", item["uncertainties"],
                    ["Multiple role hypotheses coexist."] if len(hypotheses) > 1 else [])

    # Space findings are rank-based observations, not cleaning recommendations.
    largest = sorted(observed_files, key=lambda e: (-e["logical_bytes"], e["id"]))[:10]
    if largest:
        members = [e["id"] for e in largest]
        eid = fact("largest_observed_files", members,
                   {"logical_bytes": {e["id"]: e["logical_bytes"] for e in largest}, "ranking_limit": 10})
        finding("largest_observed_files", members, [eid], "Largest observed files by logical size", "observed",
                ["Large files are not necessarily unwanted.", "The ranking covers only successfully observed files."])

    started = datetime.fromisoformat(model["scan"]["started_at"].replace("Z", "+00:00"))
    cutoff = started - timedelta(days=180)
    older = [e for e in observed_files if e["mtime_ns"] is not None
             and e["mtime_ns"] < int(cutoff.timestamp() * 10**9)]
    if older:
        members = [e["id"] for e in older]
        eid = fact("older_modification_times", members,
                   {"threshold_days": 180, "cutoff": cutoff.isoformat(), "timestamp_field": "mtime_ns"})
        finding("older_modification_times", members, [eid], "Modification times older than 180 days",
                "observed", ["Modification time does not show last use, usefulness or whether work is dormant.",
                             "Copied or manually edited timestamps may not reflect material age."])

    uncertainty_ids = [e["id"] for e in entries if e["status"] != "observed"]
    if model["scan"]["status"] != "complete" or uncertainty_ids:
        eid = fact("scan_coverage", uncertainty_ids,
                   {"status": model["scan"]["status"], "coverage": model["scan"]["coverage"],
                    "exclusions": model["scan"]["exclusions"], "errors": model["scan"]["errors"]})
        finding("incomplete_inventory", uncertainty_ids, [eid], "Some storage could not be characterised",
                "unknown", ["Missing observations cannot be interpreted as empty folders or deleted files."])

    unique = {}
    for entry in observed_files:
        unique.setdefault(entry["object_id"] or entry["id"], entry)
    identity_unknown = sum(e["object_id"] is None for e in observed_files)
    object_records = list(unique.values())
    allocated = [e["allocated_bytes"] for e in object_records if e["allocated_bytes"] is not None]
    aggregates = {
        "logical_bytes_by_path": sum(e["logical_bytes"] for e in observed_files),
        "logical_bytes_by_observed_object": (None if identity_unknown else
                                             sum(e["logical_bytes"] for e in object_records)),
        "known_allocated_bytes_by_observed_object": sum(allocated) if allocated and not identity_unknown else None,
        "allocation_unknown_objects": (None if identity_unknown else
                                       sum(e["allocated_bytes"] is None for e in object_records)),
        "object_identity_unknown_paths": identity_unknown,
        "physical_bytes": None, "recoverable_bytes": None,
        "observed_regular_files": len(observed_files),
        "distinct_observed_file_objects": None if identity_unknown else len(unique),
        "hard_link_alias_paths": None if identity_unknown else len(observed_files) - len(unique),
        "status_counts": dict(sorted(Counter(e["status"] for e in entries).items())),
        "by_extension_category": dict(sorted(categories.items())),
        "partial": model["scan"]["status"] != "complete",
        "uncertainties": ["Logical bytes count file lengths, not unique physical storage.",
                          "Stat allocation may include shared extents, compression or filesystem-specific accounting.",
                          "No recoverable-space estimate or safe-to-delete determination is made.",
                          "Unobserved entries and links outside these roots are not included.",
                          "Object-level totals are unknown when object identity is unavailable."],
    }
    for found in findings:
        if found["kind"] == "incomplete_inventory":
            continue
        members = found["member_ids"]
        uncertain = [key for key in members if by_id[key]["status"] != "observed"]
        review_id = stable_id("step", found["id"], "review")
        intent_id = stable_id("step", found["id"], "intent")
        alternatives.append({
            "id": stable_id("plan", found["id"]), "kind": "read_only_review_alternatives",
            "finding_ids": [found["id"]], "scope_member_ids": members, "executable": False,
            "alternatives": [
                {"id": "keep_current_structure", "label": "Keep the current structure",
                 "steps": [{"id": stable_id("step", found["id"], "keep"), "type": "keep_unchanged",
                            "member_ids": members, "depends_on": [], "evidence_ids": found["evidence_ids"]}],
                 "expected_consequences": {"filesystem_changes": 0, "additional_content_reads": 0},
                 "unchanged_member_ids": members, "uncertain_member_ids": uncertain},
                {"id": "review_grouping", "label": "Review the evidence and describe a possible grouping",
                 "steps": [{"id": review_id, "type": "inspect_evidence", "member_ids": members,
                            "depends_on": [], "evidence_ids": found["evidence_ids"]},
                           {"id": intent_id, "type": "ask_about_intent", "member_ids": members,
                            "depends_on": [review_id], "evidence_ids": found["evidence_ids"]}],
                 "expected_consequences": {"filesystem_changes": 0, "additional_content_reads": 0},
                 "unchanged_member_ids": members, "uncertain_member_ids": uncertain}],
            "reasons": [found["title"]], "uncertainties": found["uncertainties"],
            "outside_scope": "All other observed entries remain unchanged.",
        })
    return {"aggregates": aggregates, "directories": directories,
            "evidence": sorted(evidence, key=lambda e: e["id"]),
            "relationships": sorted(relationships, key=lambda e: e["id"]),
            "findings": sorted(findings, key=lambda e: e["id"]),
            "plan_alternatives": sorted(alternatives, key=lambda e: e["id"]),
            "analysis_coverage": {**counts, "max_findings": MAX_FINDINGS, "max_relationships": MAX_RELATIONSHIPS,
                                  "semantic_content_analysis": False}}
