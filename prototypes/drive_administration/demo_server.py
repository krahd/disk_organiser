"""Isolated loopback demonstration. Only packaged synthetic data is reviewed.

No application, executor, operation store or provider client is imported.
Decisions are stateless and reference only fixed synthetic snapshots. Pure model
validation/fixture functions are used; no scanner is called. Five fixed frontend
assets are read once at app creation, never in response to a supplied path.
"""

from __future__ import annotations

import argparse
import hmac
import ipaddress
import json
from pathlib import Path
import secrets
import copy
import sys

# Support the existing direct-script server command without importing the app.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

from fixtures import blocked_example, sample_document
from planning_preview import ContractError, digest, review, revise
from observation_adapter import AdapterError, build_observation_draft, observation_digest
from observation_demo_fixture import SCENARIO_ID, SOURCE_REVISION, aurora_scenario


SCENARIOS = {"harbour-reference": sample_document, "harbour-uncertain": blocked_example}
MAX_REQUEST_BYTES = 4096
MAX_FOLDER_CHARS = 240
REQUEST_KEYS = frozenset(("scenario_id", "expected_revision", "expected_digest", "member_ids",
                          "destination_volume_id", "destination_folder"))
SAFETY = {"synthetic": True, "executable": False, "execution_authority": None,
          "undo_available": False, "source_safe_to_erase": False,
          "live_backup_verified": False, "live_restore_verified": False}


def _strict_json(raw):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ContractError("Duplicate request field")
            result[key] = value
        return result

    def reject_constant(_value):
        raise ContractError("Invalid number")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                           parse_constant=reject_constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ContractError("Invalid request JSON") from error
    return value


def _parse_request(raw):
    value = _strict_json(raw)
    if not isinstance(value, dict) or set(value) != REQUEST_KEYS:
        raise ContractError("Only scenario, reference and decision fields are allowed")
    if not isinstance(value["scenario_id"], str) or value["scenario_id"] not in SCENARIOS:
        raise ContractError("Choose a packaged scenario")
    if type(value["expected_revision"]) is not int or value["expected_revision"] < 1:
        raise ContractError("Invalid reference revision")
    if not isinstance(value["expected_digest"], str) or len(value["expected_digest"]) != 64:
        raise ContractError("Invalid reference digest")
    members = value["member_ids"]
    if not isinstance(members, list) or not 1 <= len(members) <= 4:
        raise ContractError("Select between one and four packaged members")
    if any(not isinstance(item, str) or len(item) > 32 for item in members):
        raise ContractError("Invalid member selection")
    if len(set(members)) != len(members):
        raise ContractError("Duplicate member selection")
    if not isinstance(value["destination_volume_id"], str) or len(value["destination_volume_id"]) > 32:
        raise ContractError("Invalid destination volume")
    folder = value["destination_folder"]
    if not isinstance(folder, str) or not 1 <= len(folder) <= MAX_FOLDER_CHARS:
        raise ContractError("Use a relative folder of 1 to 240 characters")
    return value


def _reference(scenario_id):
    document = SCENARIOS[scenario_id]()
    return {"scenario_id": scenario_id, "reference_revision": document["revision"],
            "reference_digest": digest(document), "fixture_as_of": document["now"],
            "project": document["project"], "entries": document["entries"],
            "volumes": document["volumes"], "targets": document["targets"],
            "decision": document["decision"], "review": review(document), **SAFETY}



def _parse_observation_request(raw):
    value = _strict_json(raw)
    fields = {"expected_source_revision", "expected_observation_digest", "expected_reference_decision_digest",
              "member_paths", "destination_root_id", "destination_folder"}
    if type(value) is not dict or set(value) != fields:
        raise ContractError("Only the fixed observation reference and explicit decision fields are allowed")
    if type(value["expected_source_revision"]) is not int or value["expected_source_revision"] < 1:
        raise ContractError("Invalid source revision")
    for key in ("expected_observation_digest", "expected_reference_decision_digest"):
        if not isinstance(value[key], str) or len(value[key]) != 64:
            raise ContractError("Invalid observation reference digest")
    members = value["member_paths"]
    if type(members) is not list or not 1 <= len(members) <= 8:
        raise ContractError("Select between one and eight packaged choices")
    seen = set()
    for member in members:
        if type(member) is not dict or set(member) != {"entry_id", "project_path"}:
            raise ContractError("Use an explicit member ID and project-relative path")
        identifier, path = member["entry_id"], member["project_path"]
        if not isinstance(identifier, str) or not 1 <= len(identifier) <= 128 or identifier in seen:
            raise ContractError("Unknown or repeated member choice")
        if not isinstance(path, str) or not 1 <= len(path) <= MAX_FOLDER_CHARS:
            raise ContractError("Use a project-relative path of 1 to 240 characters")
        seen.add(identifier)
    if not isinstance(value["destination_root_id"], str) or not 1 <= len(value["destination_root_id"]) <= 128:
        raise ContractError("Choose a packaged observed root")
    if not isinstance(value["destination_folder"], str) or not 1 <= len(value["destination_folder"]) <= MAX_FOLDER_CHARS:
        raise ContractError("Use a relative intended folder of 1 to 240 characters")
    return value


def _observation_snapshot():
    model, decision, choices = aurora_scenario()
    source_digest = observation_digest(model)
    result = build_observation_draft(model, decision, expected_observation_digest=source_digest,
                                     now=model["scan"]["started_at"])
    return {"model": model, "decision": decision, "choices": choices,
            "observation_digest": source_digest, "reference_draft": result}


def _observation_response(snapshot, decision, *, is_reference):
    result = (copy.deepcopy(snapshot["reference_draft"]) if is_reference else
              build_observation_draft(snapshot["model"], decision,
                                      expected_observation_digest=snapshot["observation_digest"],
                                      now=snapshot["model"]["scan"]["started_at"]))
    return {"scenario_id": SCENARIO_ID, "source_revision": SOURCE_REVISION,
            "observation_digest": snapshot["observation_digest"],
            "reference_decision_digest": snapshot["reference_draft"]["decision_digest"],
            "decision_revision": 1 if is_reference else 2, "decision": copy.deepcopy(decision),
            "draft": result, "read_only": True, **SAFETY}


def _observation_reference(snapshot=None):
    snapshot = snapshot or _observation_snapshot()
    return {**_observation_response(snapshot, snapshot["decision"], is_reference=True),
            "fixture_as_of": snapshot["model"]["scan"]["started_at"],
            "choices": copy.deepcopy(snapshot["choices"]),
            "roots": copy.deepcopy(snapshot["model"]["scan"]["roots"]),
            "source_entry_count": len(snapshot["model"]["entries"]),
            "recorded_paths": [{"entry_id": entry["id"], "root_id": entry["root_id"],
                                "relative_path": entry["relative_path"]}
                               for entry in snapshot["model"]["entries"]]}


def create_demo_app(port=8765):
    """Build the standalone app; the CLI always binds 127.0.0.1, without debug."""
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Choose an unprivileged loopback port")
    app = Flask(__name__, static_folder=None)
    app.config.update(MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES)
    origin = f"http://127.0.0.1:{port}"
    host = f"127.0.0.1:{port}"
    process_token = secrets.token_urlsafe(32)
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    observation_snapshot = _observation_snapshot()
    assets = {
        "/": ((frontend / "project-review-demo.html").read_text(encoding="utf-8").replace(
            "__DEMO_PROCESS_TOKEN__", process_token), "text/html"),
        "/project-review-demo.js": ((frontend / "project-review-demo.js").read_text(encoding="utf-8"), "text/javascript"),
        "/project-review-demo.css": ((frontend / "project-review-demo.css").read_text(encoding="utf-8"), "text/css"),
        "/observation-draft": ((frontend / "project-observation-demo.html").read_text(encoding="utf-8").replace(
            "__DEMO_PROCESS_TOKEN__", process_token), "text/html"),
        "/project-observation-demo.js": ((frontend / "project-observation-demo.js").read_text(encoding="utf-8"), "text/javascript"),
    }

    def error(message, status):
        return jsonify({"error": message, **SAFETY}), status

    @app.before_request
    def boundary():
        try:
            loopback = ipaddress.ip_address(request.remote_addr).is_loopback
        except (ValueError, TypeError):
            loopback = False
        if not loopback or request.host != host or request.scheme != "http":
            return error("Loopback access only", 403)
        if request.headers.get("Origin") not in (None, origin):
            return error("Same-origin access only", 403)
        if request.headers.get("Sec-Fetch-Site") not in (None, "none", "same-origin"):
            return error("Same-origin access only", 403)
        if request.path not in {*assets, "/api/reference", "/api/review", "/api/observation/reference", "/api/observation/review"}:
            return error("Unknown demo route", 404)
        if request.path in assets and (request.method != "GET" or request.query_string):
            return error("Unsupported asset request", 400)
        if request.path.startswith("/api/"):
            supplied = request.headers.get("X-Demo-Token", "")
            if not supplied.isascii() or not hmac.compare_digest(supplied, process_token):
                return error("Reload the demo to renew its process token", 403)
            if request.path in ("/api/review", "/api/observation/review") and request.headers.get("Origin") != origin:
                return error("Same-origin review required", 403)
        return None

    @app.after_request
    def security_headers(response):
        response.headers.update({
            "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        })
        return response

    @app.errorhandler(HTTPException)
    def http_error(exception):
        return error("Demo request rejected", exception.code)

    def asset():
        content, mimetype = assets[request.path]
        return Response(content, mimetype=mimetype)

    for index, path in enumerate(assets):
        app.add_url_rule(path, f"asset_{index}", asset, methods=["GET"])

    @app.get("/api/reference")
    def reference():
        if set(request.args) != {"scenario_id"} or len(request.args.getlist("scenario_id")) != 1:
            return error("Choose one packaged scenario", 400)
        scenario_id = request.args["scenario_id"]
        if scenario_id not in SCENARIOS:
            return error("Choose a packaged scenario", 400)
        return jsonify(_reference(scenario_id))

    @app.post("/api/review")
    def review_decision():
        if request.query_string or request.mimetype != "application/json":
            return error("Use the bounded JSON decision contract", 400)
        try:
            value = _parse_request(request.get_data(cache=False))
            document = SCENARIOS[value["scenario_id"]]()
            if value["expected_revision"] != document["revision"] or value["expected_digest"] != digest(document):
                return error("Reference changed; reload this scenario before reviewing", 409)
            if not set(value["member_ids"]) <= {item["id"] for item in document["entries"]}:
                raise ContractError("Select only packaged members")
            if value["destination_volume_id"] not in {item["id"] for item in document["volumes"]}:
                raise ContractError("Choose a packaged volume")
            revised = revise(document, expected_digest=value["expected_digest"],
                             member_ids=value["member_ids"],
                             destination_volume_id=value["destination_volume_id"],
                             destination_folder=value["destination_folder"], acknowledged=True)
            return jsonify({"scenario_id": value["scenario_id"], "reference_revision": document["revision"],
                            "reference_digest": digest(document), "review": review(revised), **SAFETY})
        except ContractError as exception:
            return error(str(exception), 400)

    @app.get("/api/observation/reference")
    def observation_reference():
        if request.query_string:
            return error("Only the fixed Aurora observation scenario is available", 400)
        return jsonify(_observation_reference(observation_snapshot))

    @app.post("/api/observation/review")
    def review_observation_decision():
        if request.query_string or request.mimetype != "application/json":
            return error("Use the bounded JSON observation decision contract", 400)
        try:
            value = _parse_observation_request(request.get_data(cache=False))
            if (value["expected_source_revision"] != SOURCE_REVISION or
                    value["expected_observation_digest"] != observation_snapshot["observation_digest"] or
                    value["expected_reference_decision_digest"] != observation_snapshot["reference_draft"]["decision_digest"]):
                return error("Observation reference changed; reload this page before reviewing", 409)
            allowed = {item["entry"]["id"] for item in observation_snapshot["choices"]}
            if not {member["entry_id"] for member in value["member_paths"]} <= allowed:
                raise ContractError("Select only the eight packaged observation choices")
            if value["destination_root_id"] not in {root["id"] for root in observation_snapshot["model"]["scan"]["roots"]}:
                raise ContractError("Choose a packaged observed root")
            decision = {**copy.deepcopy(observation_snapshot["decision"]),
                        "member_paths": value["member_paths"], "destination_root_id": value["destination_root_id"],
                        "destination_folder": value["destination_folder"], "acknowledged": True}
            return jsonify(_observation_response(observation_snapshot, decision, is_reference=False))
        except (ContractError, AdapterError) as exception:
            return error(str(exception), 400)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic project review; no drives or providers connected")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    create_demo_app(args.port).run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)
