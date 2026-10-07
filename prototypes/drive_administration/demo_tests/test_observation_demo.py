"""Fixed Aurora HTTP boundary; Flask client only, no listening sockets."""

import copy
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo_server import create_demo_app, _observation_reference, _observation_snapshot, SAFETY
from observation_adapter import build_observation_draft
from observation_demo_fixture import aurora_scenario


class ObservationDemoTests(unittest.TestCase):
    def setUp(self):
        self.app = create_demo_app()
        self.app.testing = True
        self.client = self.app.test_client()
        self.origin = 'http://127.0.0.1:8765'
        response = self.client.get('/observation-draft', base_url=self.origin)
        self.token = re.search(r'name="demo-process-token" content="([^"]+)"', response.text)[1]
        self.headers = {'X-Demo-Token': self.token, 'Origin': self.origin}
        self.reference = _observation_reference()
        self.body = {'expected_source_revision': self.reference['source_revision'],
                     'expected_observation_digest': self.reference['observation_digest'],
                     'expected_reference_decision_digest': self.reference['reference_decision_digest'],
                     'member_paths': copy.deepcopy(self.reference['decision']['member_paths']),
                     'destination_root_id': self.reference['decision']['destination_root_id'],
                     'destination_folder': self.reference['decision']['destination_folder']}

    def get(self, path='/api/observation/reference', **kwargs):
        return self.client.get(path, base_url=self.origin, headers=kwargs.pop('headers', self.headers), **kwargs)

    def post(self, body=None, **kwargs):
        return self.client.post('/api/observation/review', base_url=self.origin,
                                headers=kwargs.pop('headers', self.headers),
                                json=self.body if body is None else body, **kwargs)

    def assert_incomplete(self, response):
        self.assertEqual(response.status_code, 200)
        value = response.json
        for key, expected in SAFETY.items():
            self.assertEqual(value[key], expected)
        self.assertTrue(value['read_only'])
        result = value['draft']
        self.assertEqual(result['status'], 'blocked_observation_draft')
        self.assertEqual(result['observation_digest'], value['observation_digest'])
        self.assertFalse(result['executable'])
        self.assertIsNone(result['execution_authority'])
        self.assertFalse(result['source_safe_to_erase'])
        self.assertFalse(result['undo_available'])
        for field in ('required_destination_bytes', 'known_logical_copy_bytes', 'observed_free_bytes', 'physical_allocation_prediction'):
            self.assertIsNone(result['capacity'][field])
        for field in ('configured_target_ids', 'independent_copy_count', 'project_restore_satisfied'):
            self.assertIsNone(result['protection'][field])
        self.assertFalse(result['protection']['live_backup_verified'])
        self.assertFalse(result['protection']['live_restore_verified'])

    def test_fixed_page_link_and_reference_scope(self):
        self.assertIn('href="/observation-draft"', self.get('/').text)
        response = self.get()
        self.assertEqual(response.json, self.reference)
        self.assertEqual(len(response.json['roots']), 2)
        self.assertEqual(len(response.json['choices']), 8)
        self.assertEqual(response.json['source_entry_count'], 32)
        self.assertEqual(response.json['decision_revision'], 1)
        self.assertIn('stale', {root['status'] for root in response.json['roots']})
        self.assert_incomplete(response)
        for query in ('?path=/tmp', '?scenario_id=anything', '?synthetic=false', '?file=../../../etc/passwd'):
            self.assertEqual(self.get('/api/observation/reference' + query).status_code, 400)

    def test_exact_python_adapter_is_used_for_explicit_decisions(self):
        body = {**self.body, 'destination_folder': 'Reviewed Aurora',
                'member_paths': [self.body['member_paths'][0], {'entry_id': self.reference['choices'][3]['entry']['id'], 'project_path': 'Unresolved/asset.data'}]}
        response = self.post(body)
        model, original, _choices = aurora_scenario()
        decision = {**original, 'member_paths': body['member_paths'], 'destination_root_id': body['destination_root_id'], 'destination_folder': body['destination_folder']}
        expected = build_observation_draft(model, decision, expected_observation_digest=body['expected_observation_digest'], now=model['scan']['started_at'])
        self.assertEqual(response.json['draft'], expected)
        self.assertEqual(response.json['decision'], decision)
        self.assertEqual(response.json['decision_revision'], 2)
        self.assertIn('unsupported_member_kind', {item['code'] for item in expected['blockers']})
        self.assert_incomplete(response)

    def test_reference_is_immutable_across_repeated_reviews(self):
        before = self.get().json
        for folder in ('First', 'Second', 'Third'):
            response = self.post({**self.body, 'destination_folder': folder})
            self.assertEqual(response.json['source_revision'], 1)
            self.assertEqual(response.json['decision_revision'], 2)
            self.assertEqual(response.json['observation_digest'], before['observation_digest'])
            self.assertEqual(response.json['reference_decision_digest'], before['reference_decision_digest'])
        self.assertEqual(self.get().json, before)

    def test_all_reference_fields_guard_stale_or_conflicting_requests(self):
        for key, value in [('expected_source_revision', 2), ('expected_observation_digest', '0' * 64),
                           ('expected_reference_decision_digest', '0' * 64)]:
            with self.subTest(key=key):
                response = self.post({**self.body, key: value})
                self.assertEqual(response.status_code, 409)
                self.assertFalse(response.json['executable'])
        self.assertEqual(self.get().json, self.reference)

    def test_known_but_unlisted_observation_cannot_expand_scope(self):
        snapshot = _observation_snapshot()
        choices = {item['entry']['id'] for item in snapshot['choices']}
        unlisted = next(entry['id'] for entry in snapshot['model']['entries'] if entry['id'] not in choices)
        response = self.post({**self.body, 'member_paths': [{'entry_id': unlisted, 'project_path': 'unlisted'}]})
        self.assertEqual(response.status_code, 400)

    def test_exact_current_address_never_becomes_a_successful_noop(self):
        choice = self.reference['choices'][0]
        response = self.post({**self.body, 'member_paths': [{'entry_id': choice['entry']['id'], 'project_path': 'design_v1.blend'}],
                              'destination_root_id': choice['entry']['root_id'], 'destination_folder': 'Project Aurora'})
        self.assertEqual(response.json['draft']['members'][0]['placement'], 'current_address_requires_identity')
        self.assertIn('observed_target_path_overlap', {item['code'] for item in response.json['draft']['blockers']})
        self.assert_incomplete(response)

    def test_unreadable_members_and_aliases_keep_uncertainty(self):
        chosen = [self.reference['choices'][index] for index in (3, 5, 6)]
        members = [{'entry_id': item['entry']['id'], 'project_path': item['default_project_path']} for item in chosen]
        response = self.post({**self.body, 'member_paths': members})
        codes = {item['code'] for item in response.json['draft']['blockers']}
        self.assertTrue({'member_not_observed', 'unsupported_member_kind', 'link_identity_unresolved'} <= codes)
        self.assertIn(chosen[0]['entry']['id'], response.json['draft']['capacity']['unknown_size_member_ids'])
        self.assertEqual(len(response.json['draft']['members']), 3)
        self.assert_incomplete(response)

    def test_strict_member_decision_and_reference_types(self):
        for members in ([], [self.body['member_paths'][0]] * 2, [self.body['member_paths'][0]] * 9, 'all', [None],
                        [{'entry_id': [], 'project_path': 'x'}], [{'entry_id': 'unknown', 'project_path': 'x'}],
                        [{'entry_id': self.body['member_paths'][0]['entry_id'], 'project_path': 'x', 'copy': True}]):
            with self.subTest(members=members):
                self.assertEqual(self.post({**self.body, 'member_paths': members}).status_code, 400)
        for key, values in [('expected_source_revision', [True, 0, None, '1', 1.5]),
                            ('expected_observation_digest', [None, [], 'x' * 65]),
                            ('expected_reference_decision_digest', [None, {}, '']),
                            ('destination_root_id', [None, [], 'unknown'])]:
            for value in values:
                with self.subTest(key=key, value=value):
                    self.assertEqual(self.post({**self.body, key: value}).status_code, 400)

    def test_relative_path_bounds_and_text_only_names(self):
        for path in ('', '/absolute', '../parent', 'C:/drive', 'a\\b', 'a//b', 'a/./b', 'a\nb', 'x' * 241):
            for field in ('destination_folder', 'project_path'):
                body = copy.deepcopy(self.body)
                if field == 'project_path': body['member_paths'][0][field] = path
                else: body[field] = path
                with self.subTest(path=path, field=field):
                    self.assertEqual(self.post(body).status_code, 400)
        text = '<img src=x onerror=alert(1)>'
        response = self.post({**self.body, 'destination_folder': text})
        self.assertEqual(response.mimetype, 'application/json')
        self.assertIn(text, response.json['draft']['members'][0]['intended']['relative_path'])
        self.assert_incomplete(response)

    def test_evidence_clock_providers_and_execution_cannot_be_submitted(self):
        for key in ('model', 'entries', 'roots', 'synthetic', 'source_revision', 'now', 'max_observation_age_hours',
                    'volume_id', 'backups', 'credentials', 'provider', 'execute', 'acknowledged', 'project_id', 'project_label'):
            with self.subTest(key=key):
                self.assertEqual(self.post({**self.body, key: True}).status_code, 400)

    def test_duplicate_malformed_deep_and_oversized_json(self):
        raw = json.dumps(self.body)
        for data in (b'\xff', '{', raw[:-1] + ',"destination_folder":"duplicate"}', '{"x":NaN}', '[' * 1100 + ']' * 1100):
            response = self.client.post('/api/observation/review', base_url=self.origin, headers=self.headers, data=data, content_type='application/json')
            self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/observation/review', base_url=self.origin, headers=self.headers, data='x' * 4097, content_type='application/json')
        self.assertEqual(response.status_code, 413)

    def test_same_process_token_origin_host_and_methods_are_required(self):
        for token in ('', 'wrong', 'é'):
            self.assertEqual(self.get(headers={**self.headers, 'X-Demo-Token': token}).status_code, 403)
        for origin in (None, 'null', 'http://localhost:8765', 'https://evil.example'):
            headers = {'X-Demo-Token': self.token}
            if origin is not None: headers['Origin'] = origin
            self.assertEqual(self.post(headers=headers).status_code, 403)
        for path in ('/observation-draft', '/project-observation-demo.js', '/api/observation/reference'):
            self.assertEqual(self.get(path, headers={**self.headers, 'Sec-Fetch-Site': 'cross-site'}).status_code, 403)
            self.assertEqual(self.get(path, environ_overrides={'REMOTE_ADDR': '203.0.113.9'}).status_code, 403)
        for base in ('http://localhost:8765', 'http://127.0.0.1:8000', 'https://127.0.0.1:8765'):
            self.assertEqual(self.client.get('/observation-draft', base_url=base).status_code, 403)
        self.assertEqual(self.get('/api/observation/review').status_code, 405)
        self.assertEqual(self.client.post('/api/observation/reference', base_url=self.origin, headers=self.headers, json={}).status_code, 405)
        self.assertEqual(self.client.post('/api/observation/review?extra=x', base_url=self.origin, headers=self.headers, json=self.body).status_code, 400)
        self.assertEqual(self.client.post('/api/observation/review', base_url=self.origin, headers=self.headers, data=json.dumps(self.body)).status_code, 400)
        other = create_demo_app().test_client()
        self.assertEqual(other.get('/api/observation/reference', base_url=self.origin, headers=self.headers).status_code, 403)

    def test_no_request_time_files_scanner_network_or_planner_calls(self):
        with patch('builtins.open', side_effect=AssertionError('unexpected file')), \
             patch('pathlib.Path.open', side_effect=AssertionError('unexpected file')), \
             patch('socket.socket', side_effect=AssertionError('unexpected network')), \
             patch('os.open', side_effect=AssertionError('unexpected path')), \
             patch('os.stat', side_effect=AssertionError('unexpected stat')), \
             patch('backend.disk_model.scan_storage', side_effect=AssertionError('unexpected scan')), \
             patch('planning_preview.review', side_effect=AssertionError('unexpected planner')), \
             patch('demo_server.review', side_effect=AssertionError('unexpected bound planner')), \
             patch('demo_server.revise', side_effect=AssertionError('unexpected bound revision')):
            self.assertEqual(self.get('/observation-draft').status_code, 200)
            self.assert_incomplete(self.get())
            self.assert_incomplete(self.post())
        self.assertFalse(any(name in sys.modules for name in ('backend.app', 'backend.guided', 'backend.op_store')))

    def test_harbour_response_contract_is_unchanged(self):
        from demo_server import _reference
        self.assertEqual(self.get('/api/reference?scenario_id=harbour-reference').json, _reference('harbour-reference'))
        self.assertEqual(self.get('/api/reference?scenario_id=aurora-observation').status_code, 400)

    def test_frontend_fixture_matches_exact_packaged_response(self):
        path = Path(__file__).resolve().parents[3] / 'frontend/__tests__/project-observation-fixture.json'
        self.assertEqual(json.loads(path.read_text()), self.reference)


if __name__ == '__main__':
    unittest.main()
