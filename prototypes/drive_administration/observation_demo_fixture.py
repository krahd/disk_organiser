"""One fixed Aurora scenario derived in memory from the canonical synthetic model.

No input path is opened, no scan runs, and no real observation is relabelled.
"""

import copy
from collections import Counter

from backend.disk_model import compare_inventory
from backend.disk_model_analysis import analyse_inventory
from backend.disk_model_fixture import synthetic_model


SCENARIO_ID = "aurora-observation"
SOURCE_REVISION = 1
SECOND_ROOT = "root_synthetic_aurora_secondary"


def aurora_scenario():
    model = synthetic_model()
    first_root = model["scan"]["roots"][0]["id"]
    second = copy.deepcopy(model["scan"]["roots"][0])
    second.update(id=SECOND_ROOT, path="/synthetic/aurora-secondary", status="stale")
    model["scan"]["roots"].append(second)
    extra = copy.deepcopy(model["entries"])
    ids = {entry["id"]: "secondary_" + entry["id"] for entry in extra}
    for entry in extra:
        entry["id"] = ids[entry["id"]]
        entry["root_id"] = SECOND_ROOT
        if entry["parent_id"] is not None:
            entry["parent_id"] = ids[entry["parent_id"]]
        if entry["status"] == "observed":
            entry["status"] = "stale"
        if entry["hash"]["status"] == "verified":
            entry["hash"].update(status="stale", value=None)
        entry["uncertainties"].append("Fabricated last-known record; current availability is unverified.")
    model["entries"].extend(extra)
    model["entries"].sort(key=lambda entry: (entry["root_id"], entry["relative_path"]))
    model["scan"]["errors"].extend({**error, "entry_id": ids[error["entry_id"]]}
                                    for error in list(model["scan"]["errors"]))
    model["scan"]["id"] = "scan_synthetic_aurora_observation_v1"
    model["scan"]["uncertainties"].append("Two observed roots do not establish two physical drives or independent copies.")
    entries = model["entries"]
    model["scan"]["coverage"].update(
        entries_observed=len(entries), status_counts=dict(Counter(entry["status"] for entry in entries)),
        hash_status_counts=dict(Counter(entry["hash"]["status"] for entry in entries if entry["kind"] == "file")),
        hashed_files=sum(entry["hash"]["status"] == "verified" for entry in entries),
        hash_attempts=sum(entry["hash"]["status"] in ("verified", "stale") for entry in entries),
        hashed_bytes=sum(entry["logical_bytes"] or 0 for entry in entries if entry["hash"]["status"] == "verified"))
    model["changes"] = compare_inventory(None, model)
    model.update(analyse_inventory(model))
    lookup = {(entry["root_id"], entry["relative_path"]): entry for entry in entries}
    choices = []
    for root, path, project_path, included in [
        (first_root, "Project Aurora/design_v1.blend", "design_v1.blend", True),
        (SECOND_ROOT, "Project Aurora/design_v2.blend", "design_v2.blend", True),
        (first_root, "Project Aurora/pyproject.toml", "pyproject.toml", True),
        (first_root, "unclassified/not-readable.data", "Unresolved/not-readable.data", False),
        (SECOND_ROOT, "Inbox/receipt.pdf", "Notes/receipt.pdf", False),
        (first_root, "Archive/reference.txt", "Reference/reference.txt", False),
        (first_root, "Archive/reference-alias.txt", "Reference/reference-alias.txt", False),
        (SECOND_ROOT, "unclassified/unknown.data", "Unclassified/unknown.data", False),
    ]:
        choices.append({"entry": copy.deepcopy(lookup[(root, path)]),
                        "default_project_path": project_path, "reference_included": included})
    decision = {"project_id": "aurora", "project_label": "Aurora project",
                "member_paths": [{"entry_id": item["entry"]["id"], "project_path": item["default_project_path"]}
                                 for item in choices if item["reference_included"]],
                "destination_root_id": SECOND_ROOT, "destination_folder": "Projects/Aurora", "acknowledged": True}
    return model, decision, choices
