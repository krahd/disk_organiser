"""Isolated loopback demonstration. Only packaged synthetic data is reviewed.

No runtime module, scanner, operation store or provider client is imported.
Decisions are stateless: each request revises its immutable fixture reference.
Only the three fixed frontend assets are read, once when the app is created.
"""

from __future__ import annotations

import argparse
import hmac
import ipaddress
import json
from pathlib import Path
import secrets

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

from fixtures import blocked_example, sample_document
from planning_preview import ContractError, digest, review, revise


SCENARIOS = {"harbour-reference": sample_document, "harbour-uncertain": blocked_example}
MAX_REQUEST_BYTES = 4096
MAX_FOLDER_CHARS = 240
REQUEST_KEYS = frozenset(("scenario_id", "expected_revision", "expected_digest", "member_ids",
                          "destination_volume_id", "destination_folder"))
SAFETY = {"synthetic": True, "executable": False, "execution_authority": None,
          "undo_available": False, "source_safe_to_erase": False,
          "live_backup_verified": False, "live_restore_verified": False}


def _parse_request(raw):
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
    assets = {
        "/": ((frontend / "project-review-demo.html").read_text(encoding="utf-8").replace(
            "__DEMO_PROCESS_TOKEN__", process_token), "text/html"),
        "/project-review-demo.js": ((frontend / "project-review-demo.js").read_text(encoding="utf-8"), "text/javascript"),
        "/project-review-demo.css": ((frontend / "project-review-demo.css").read_text(encoding="utf-8"), "text/css"),
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
        if request.path not in {*assets, "/api/reference", "/api/review"}:
            return error("Unknown demo route", 404)
        if request.path in assets and (request.method != "GET" or request.query_string):
            return error("Unsupported asset request", 400)
        if request.path.startswith("/api/"):
            supplied = request.headers.get("X-Demo-Token", "")
            if not supplied.isascii() or not hmac.compare_digest(supplied, process_token):
                return error("Reload the demo to renew its process token", 403)
            if request.path == "/api/review" and request.headers.get("Origin") != origin:
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

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic project review; no drives or providers connected")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    create_demo_app(args.port).run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)
