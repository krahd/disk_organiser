"""Bounded HTTP contract tests; Flask test client only, no listening sockets."""

import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo_server import create_demo_app, _reference, SAFETY
from fixtures import sample_document
from planning_preview import digest, review, revise


class DemoServerTests(unittest.TestCase):
    def setUp(self):
        self.app = create_demo_app()
        self.app.testing = True
        self.client = self.app.test_client()
        self.origin = "http://127.0.0.1:8765"
        response = self.client.get("/", base_url=self.origin)
        self.token = re.search(r'name="demo-process-token" content="([^"]+)"', response.text)[1]
        self.headers = {"X-Demo-Token": self.token, "Origin": self.origin}
        reference = _reference("harbour-reference")
        self.body = {"scenario_id": reference["scenario_id"],
                     "expected_revision": reference["reference_revision"],
                     "expected_digest": reference["reference_digest"],
                     "member_ids": ["edit", "media", "notes"],
                     "destination_volume_id": "archive", "destination_folder": "Client projects/Harbour"}

    def get(self, path, **kwargs):
        return self.client.get(path, base_url=self.origin, headers=kwargs.pop("headers", self.headers), **kwargs)

    def post(self, body=None, **kwargs):
        return self.client.post("/api/review", base_url=self.origin,
                                headers=kwargs.pop("headers", self.headers),
                                json=self.body if body is None else body, **kwargs)

    def assert_safe(self, response):
        for key, value in SAFETY.items():
            self.assertEqual(response.json[key], value)
        if "review" in response.json:
            result = response.json["review"]
            for key in ("synthetic", "executable", "execution_authority", "undo_available", "source_safe_to_erase"):
                self.assertEqual(result[key], SAFETY[key])
            self.assertFalse(result["protection"]["live_backup_verified"])
            self.assertFalse(result["protection"]["live_restore_verified"])

    def test_only_nine_routes_and_five_fixed_assets(self):
        self.assertEqual({rule.rule for rule in self.app.url_map.iter_rules()},
                         {"/", "/project-review-demo.js", "/project-review-demo.css", "/api/reference", "/api/review",
                          "/observation-draft", "/project-observation-demo.js", "/api/observation/reference", "/api/observation/review"})
        for path in ("/", "/project-review-demo.js", "/project-review-demo.css", "/observation-draft", "/project-observation-demo.js"):
            response = self.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("default-src 'none'", response.headers["Content-Security-Policy"])
            self.assertNotIn("unsafe-inline", response.headers["Content-Security-Policy"])
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")
            self.assertNotIn("Access-Control-Allow-Origin", response.headers)
        for path in ("/static/foo", "/backend/app.py", "/../STATUS.md", "/api/scan", "/api/apply", "/api/undo", "/api/restore", "/api/upload", "/project-review-example.json"):
            response = self.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn(path, response.text)

    def test_loopback_remote_and_exact_host_only(self):
        for base in ("http://localhost:8765", "http://evil.example:8765", "http://127.0.0.1:8000", "https://127.0.0.1:8765"):
            self.assertEqual(self.client.get("/", base_url=base).status_code, 403)
        for remote in ("203.0.113.4", "", "invalid"):
            self.assertEqual(self.get("/", environ_overrides={"REMOTE_ADDR": remote}).status_code, 403)

    def test_token_required_and_rotated_per_process(self):
        for token in ("", "wrong", "é", "x" * 400):
            self.assertEqual(self.get("/api/reference?scenario_id=harbour-reference", headers={"X-Demo-Token": token}).status_code, 403)
        other = create_demo_app().test_client()
        self.assertEqual(other.get("/api/reference?scenario_id=harbour-reference", base_url=self.origin, headers=self.headers).status_code, 403)

    def test_same_origin_and_fetch_metadata(self):
        for path in ("/", "/project-review-demo.js", "/api/reference?scenario_id=harbour-reference"):
            self.assertEqual(self.get(path, headers={**self.headers, "Origin": "https://evil.example"}).status_code, 403)
            for site in ("cross-site", "same-site"):
                self.assertEqual(self.get(path, headers={**self.headers, "Sec-Fetch-Site": site}).status_code, 403)
        for origin in (None, "null", "http://localhost:8765"):
            headers = {"X-Demo-Token": self.token}
            if origin is not None:
                headers["Origin"] = origin
            self.assertEqual(self.post(headers=headers).status_code, 403)

    def test_reference_only_two_scenarios(self):
        for scenario in ("harbour-reference", "harbour-uncertain"):
            response = self.get("/api/reference?scenario_id=" + scenario)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, _reference(scenario))
            self.assert_safe(response)
        for query in ("", "?scenario_id=unknown", "?scenario_id=../../file", "?scenario_id=harbour-reference&path=/tmp", "?scenario_id=harbour-reference&scenario_id=harbour-uncertain"):
            self.assertEqual(self.get("/api/reference" + query).status_code, 400)

    def test_calls_accepted_revise_and_review_without_reimplementing_rules(self):
        body = {**self.body, "member_ids": ["edit", "notes", "extra"], "destination_folder": "Revised Harbour"}
        response = self.post(body)
        expected = review(revise(sample_document(), expected_digest=body["expected_digest"],
                                 member_ids=body["member_ids"], destination_volume_id="archive",
                                 destination_folder=body["destination_folder"], acknowledged=True))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["review"], expected)
        self.assertEqual(expected["membership_corrections"], {"added": ["extra"], "removed": ["media"]})
        self.assertIn("project_dependency_not_selected", [item["code"] for item in expected["blockers"]])
        self.assert_safe(response)

    def test_same_home_is_explicit_declared_keep_current(self):
        response = self.post({**self.body, "destination_volume_id": "working", "destination_folder": "Projects/Harbour"})
        result = response.json["review"]
        self.assertEqual(result["blockers"], [])
        self.assertEqual({item["proposal"] for item in result["proposed_changes"]}, {"keep_current"})
        self.assertEqual(result["capacity"]["known_logical_copy_bytes"], 0)
        self.assertEqual(result["capacity"]["required_destination_bytes"], 0)
        self.assert_safe(response)

    def test_different_target_below_existing_file_remains_occupied(self):
        response = self.post({**self.body, "destination_volume_id": "working", "destination_folder": "Projects/Harbour/edit.project"})
        result = response.json["review"]
        self.assertIn("occupied_name_or_ancestor_collision", [item["code"] for item in result["blockers"]])
        self.assertEqual({item["proposal"] for item in result["proposed_changes"]}, {"copy_with_project_structure"})
        self.assertGreater(result["capacity"]["required_destination_bytes"], 0)
        self.assert_safe(response)

    def test_uncertain_same_home_retains_identity_and_protection_gaps(self):
        reference = _reference("harbour-uncertain")
        response = self.post({**self.body, "scenario_id": reference["scenario_id"],
                              "expected_digest": reference["reference_digest"],
                              "destination_volume_id": "working", "destination_folder": "Projects/Harbour"})
        result = response.json["review"]
        proposals = {item["member_id"]: item["proposal"] for item in result["proposed_changes"]}
        self.assertEqual(proposals, {"edit": "keep_current", "media": "unresolved_current_location", "notes": "keep_current"})
        self.assertIsNone(result["capacity"]["required_destination_bytes"])
        self.assertIn("current_location_identity_unproven", [item["code"] for item in result["blockers"]])
        self.assertFalse(result["protection"]["project_restore_satisfied_in_fixture"])
        self.assert_safe(response)

    def test_offline_destination_and_capacity_unknown_remain_blocked(self):
        response = self.post({**self.body, "destination_volume_id": "shelf"})
        codes = {item["code"] for item in response.json["review"]["blockers"]}
        self.assertTrue({"destination_not_online", "destination_capacity_unknown"} <= codes)
        self.assert_safe(response)

    def test_stale_and_conflicting_references(self):
        for change in ({"expected_revision": 2}, {"expected_digest": "0" * 64}, {"scenario_id": "harbour-uncertain"}):
            response = self.post({**self.body, **change})
            self.assertEqual(response.status_code, 409)
            self.assert_safe(response)

    def test_stateless_reviews_never_change_the_reference(self):
        original = self.get("/api/reference?scenario_id=harbour-reference").json
        self.assertEqual(self.post({**self.body, "destination_folder": "First"}).json["review"]["revision"], 2)
        second = self.post({**self.body, "destination_folder": "Second"})
        self.assertEqual(second.json["review"]["revision"], 2)
        self.assertEqual(self.get("/api/reference?scenario_id=harbour-reference").json, original)
        self.assertEqual(digest(sample_document()), self.body["expected_digest"])

    def test_membership_types_and_bounds(self):
        for members in ([], ["unknown"], ["edit", "edit"], ["edit"] * 5, [None], [{}], "edit", True):
            with self.subTest(members=members):
                response = self.post({**self.body, "member_ids": members})
                self.assertEqual(response.status_code, 400)
                self.assert_safe(response)

    def test_destination_validation_is_bounded_and_relative(self):
        for folder in ("", "/absolute", "../parent", "C:/drive", "a//b", "a/./b", "x\\y", "a\nb", "x" * 241, None, []):
            with self.subTest(folder=folder):
                self.assertEqual(self.post({**self.body, "destination_folder": folder}).status_code, 400)
        self.assertEqual(self.post({**self.body, "destination_folder": "x" * 240}).status_code, 200)
        for volume in ("unknown", {}, None, "x" * 33):
            self.assertEqual(self.post({**self.body, "destination_volume_id": volume}).status_code, 400)

    def test_nonportable_text_stays_data_and_is_blocked(self):
        response = self.post({**self.body, "destination_folder": '<img src=x onerror=alert(1)>'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        self.assertIn("nonportable_destination_name", [item["code"] for item in response.json["review"]["blockers"]])

    def test_extra_fields_cannot_edit_evidence_or_request_execution(self):
        for key in ("backups", "restores", "entries", "policy", "document", "path", "execute", "acknowledged", "credentials", "url"):
            self.assertEqual(self.post({**self.body, key: []}).status_code, 400)
        for value in ([], None, True, "hello"):
            response = self.client.post("/api/review", base_url=self.origin, headers=self.headers,
                                        data=json.dumps(value), content_type="application/json")
            self.assertEqual(response.status_code, 400)

    def test_revision_and_digest_types(self):
        for revision in (True, None, -1, "1", {}, 1.2):
            self.assertEqual(self.post({**self.body, "expected_revision": revision}).status_code, 400)
        for value in (None, [], "", "x" * 65):
            self.assertEqual(self.post({**self.body, "expected_digest": value}).status_code, 400)
        for scenario in (None, [], {}, "unknown"):
            self.assertEqual(self.post({**self.body, "scenario_id": scenario}).status_code, 400)

    def test_invalid_duplicate_deep_and_oversized_json(self):
        raw = json.dumps(self.body)
        for data in (b'\xff', "{", raw[:-1] + ',"scenario_id":"harbour-reference"}', '{"x":NaN}', '[' * 1100 + ']' * 1100):
            response = self.client.post("/api/review", base_url=self.origin, headers=self.headers,
                                        data=data, content_type="application/json")
            self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/review", base_url=self.origin, headers=self.headers,
                                    data="x" * 4097, content_type="application/json")
        self.assertEqual(response.status_code, 413)
        self.assert_safe(response)

    def test_no_extra_query_methods_or_mime(self):
        self.assertEqual(self.get("/?file=STATUS.md").status_code, 400)
        self.assertEqual(self.client.post("/api/review?extra=x", base_url=self.origin, headers=self.headers, json=self.body).status_code, 400)
        self.assertEqual(self.client.post("/api/review", base_url=self.origin, headers=self.headers, data=json.dumps(self.body)).status_code, 400)
        self.assertEqual(self.get("/api/review").status_code, 405)
        self.assertEqual(self.client.post("/api/reference", base_url=self.origin, headers=self.headers, json={}).status_code, 405)

    def test_no_request_time_file_or_network_access(self):
        with patch("builtins.open", side_effect=AssertionError("unexpected open")), \
             patch("pathlib.Path.open", side_effect=AssertionError("unexpected file read")), \
             patch("socket.socket", side_effect=AssertionError("unexpected socket")):
            self.assertEqual(self.get("/").status_code, 200)
            self.assertEqual(self.get("/api/reference?scenario_id=harbour-reference").status_code, 200)
            self.assertEqual(self.post().status_code, 200)
        self.assertFalse(any(name in sys.modules for name in ("backend.app", "backend.guided", "backend.op_store")))

    def test_frontend_test_fixtures_match_packaged_reference(self):
        path = Path(__file__).resolve().parents[3] / "frontend" / "__tests__" / "project-review-fixtures.json"
        self.assertEqual(json.loads(path.read_text()), {name: _reference(name) for name in ("harbour-reference", "harbour-uncertain")})

    def test_invalid_listening_ports(self):
        for port in (0, 80, 65536, True, "8765"):
            with self.assertRaises(ValueError):
                create_demo_app(port)


if __name__ == "__main__":
    unittest.main()
