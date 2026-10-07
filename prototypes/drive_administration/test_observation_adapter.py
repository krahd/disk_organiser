"""Pure synthetic adapter acceptance. Fixtures are data; no native scan is run."""

import copy
import json
from collections import Counter
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

# The established standard-library workflow runs from this prototype directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.disk_model import compare_inventory, validate_inventory
from backend.disk_model_analysis import analyse_inventory
from observation_adapter import AdapterError, build_observation_draft, observation_digest
from planning_preview import ContractError, review


FIXTURE = Path(__file__).resolve().parents[2] / 'backend/tests/fixtures/disk-model-v1.json'
CANONICAL = json.loads(FIXTURE.read_text())
NOW = CANONICAL['scan']['started_at']


def refresh(model):
    """Update fabricated bookkeeping after explicit in-memory test mutations."""
    entries = model['entries']
    scan = model['scan']
    scan['coverage'].update(
        entries_observed=len(entries),
        status_counts=dict(Counter(e['status'] for e in entries)),
        hash_status_counts=dict(Counter(e['hash']['status'] for e in entries if e['kind'] == 'file')),
        hashed_files=sum(e['hash']['status'] == 'verified' for e in entries),
        hash_attempts=sum(e['hash']['status'] == 'verified' for e in entries),
        hashed_bytes=sum(e['logical_bytes'] or 0 for e in entries if e['hash']['status'] == 'verified'),
        complete_within_policy=scan['status'] == 'complete')
    model['changes'] = compare_inventory(None, model)
    model.update(analyse_inventory(model))
    return model


def multi_root():
    model = copy.deepcopy(CANONICAL)
    root = copy.deepcopy(model['scan']['roots'][0])
    root.update(id='root_synthetic_archive', path='/synthetic/archive')
    model['scan']['roots'].append(root)
    extra = copy.deepcopy(model['entries'])
    ids = {entry['id']: 'second_' + entry['id'] for entry in extra}
    for entry in extra:
        entry['id'] = ids[entry['id']]
        entry['root_id'] = root['id']
        if entry['parent_id'] is not None:
            entry['parent_id'] = ids[entry['parent_id']]
        # Retain opaque object/fingerprint assertions deliberately: matching
        # observations across roots must never become separate physical volumes.
    model['entries'].extend(extra)
    model['scan']['errors'].extend({**error, 'entry_id': ids[error['entry_id']]} for error in list(model['scan']['errors']))
    model['scan']['id'] = 'scan_synthetic_multi_root'
    return refresh(model)


def dense_case(count):
    """Valid, flat synthetic observations with adversarial nested intent paths."""
    model = copy.deepcopy(CANONICAL)
    root = next(e for e in model['entries'] if e['relative_path'] == '.')
    template = next(e for e in model['entries'] if e['relative_path'] == 'Project Aurora/design_v1.blend')
    model['entries'] = [root]
    for number in range(count):
        entry = copy.deepcopy(template)
        entry.update(id=f'entry_{number}', relative_path=f'file{number}', parent_id=root['id'],
                     object_id=None, fingerprint=None,
                     hash={'status': 'disabled', 'algorithm': None, 'value': None})
        model['entries'].append(entry)
    for field in ('directories', 'evidence', 'findings', 'relationships', 'plan_alternatives'):
        model[field] = []
    model['scan'].update(errors=[], exclusions=[], status='complete')
    model['scan']['coverage'].update(
        entries_observed=count + 1, status_counts={'observed': count + 1},
        hash_status_counts={'disabled': count}, hashed_files=0, hash_attempts=0, hashed_bytes=0,
        complete_within_policy=True, stop_reason=None)
    model['changes'] = compare_inventory(None, model)
    decision = {'project_id': 'dense', 'project_label': 'Dense synthetic project',
                'member_paths': [{'entry_id': f'entry_{number}', 'project_path': '/'.join(['x'] * (number + 1))}
                                 for number in range(count)],
                'destination_root_id': root['root_id'], 'destination_folder': 'New', 'acknowledged': True}
    return model, decision


def entry_at(model, path='Project Aurora/design_v1.blend', root=None):
    root = root or model['scan']['roots'][0]['id']
    return next(entry for entry in model['entries'] if entry['relative_path'] == path and entry['root_id'] == root)


def decision_for(model):
    entry = entry_at(model)
    return {'project_id': 'aurora', 'project_label': 'Aurora project',
            'member_paths': [{'entry_id': entry['id'], 'project_path': 'design_v1.blend'}],
            'destination_root_id': entry['root_id'], 'destination_folder': 'Project Aurora', 'acknowledged': True}


def draft(model, decision=None, **kwargs):
    return build_observation_draft(model, decision or decision_for(model),
                                   expected_observation_digest=observation_digest(model), now=kwargs.pop('now', NOW), **kwargs)


def codes(result):
    return {item['code'] for item in result['blockers']}


class ObservationAdapterTests(unittest.TestCase):
    def assert_incomplete(self, result):
        self.assertEqual(result['status'], 'blocked_observation_draft')
        self.assertTrue(result['synthetic'])
        self.assertTrue(result['read_only'])
        self.assertFalse(result['executable'])
        self.assertIsNone(result['execution_authority'])
        self.assertFalse(result['undo_available'])
        self.assertFalse(result['source_safe_to_erase'])
        for name in ('known_logical_copy_bytes', 'required_destination_bytes', 'observed_free_bytes', 'physical_allocation_prediction'):
            self.assertIsNone(result['capacity'][name])
        self.assertEqual(result['capacity']['reclaimed_bytes'], 0)
        self.assertIsNone(result['protection']['configured_target_ids'])
        self.assertIsNone(result['protection']['independent_copy_count'])
        self.assertIsNone(result['protection']['project_restore_satisfied'])
        self.assertFalse(result['protection']['live_backup_verified'])
        self.assertFalse(result['protection']['live_restore_verified'])
        self.assertTrue({'physical_volume_identity_unestablished', 'volume_name_semantics_unknown',
                         'current_root_availability_unverified', 'content_version_unverified',
                         'project_dependencies_unknown', 'destination_capacity_unknown',
                         'backup_evidence_unavailable', 'restore_evidence_unavailable'} <= codes(result))
        for member in result['members']:
            self.assertIsNone(member['volume_id'])
            self.assertIsNone(member['content_version'])
            self.assertEqual(member['dependency_coverage'], 'unknown')
            self.assertTrue(member['source_retained'])
            self.assertNotIn('proposal', member)

    def test_canonical_export_produces_separate_incomplete_draft(self):
        model = copy.deepcopy(CANONICAL)
        validate_inventory(model)
        with self.assertRaises(ContractError):
            review(model)
        result = draft(model)
        self.assertEqual(result['schema_version'], 'disk-administration-observation-draft/v1')
        self.assertEqual(result['project'], {'id': 'aurora', 'label': 'Aurora project'})
        self.assertEqual(result['members'][0]['source']['relative_path'], 'Project Aurora/design_v1.blend')
        self.assertEqual(result['members'][0]['intended']['relative_path'], 'Project Aurora/design_v1.blend')
        self.assertEqual(result['members'][0]['placement'], 'current_address_requires_identity')
        self.assertIn('observed_target_path_overlap', codes(result))
        with self.assertRaises(ContractError):
            review(result)
        self.assert_incomplete(result)

    def test_explicit_multi_root_membership_preserves_each_observation(self):
        model = multi_root()
        decision = decision_for(model)
        second = entry_at(model, root='root_synthetic_archive')
        decision['member_paths'].append({'entry_id': second['id'], 'project_path': 'Second/design.blend'})
        result = draft(model, decision)
        self.assertEqual(len(result['observed_roots']), 2)
        self.assertEqual(len(result['members']), 2)
        self.assertEqual({m['source']['root_id'] for m in result['members']}, {r['id'] for r in model['scan']['roots']})
        self.assertEqual(result['capacity']['known_recorded_path_logical_bytes'], 42)
        self.assert_incomplete(result)

    def test_matching_root_paths_and_fingerprints_do_not_merge_volumes(self):
        model = multi_root()
        model['scan']['roots'][1]['path'] = model['scan']['roots'][0]['path']
        result = draft(model)
        self.assertEqual(len(result['observed_roots']), 2)
        self.assertEqual(result['observed_roots'][0]['identity'], result['observed_roots'][1]['identity'])
        self.assert_incomplete(result)

    def test_opaque_alias_paths_are_not_independent_protection_or_deduplicated_bytes(self):
        model = copy.deepcopy(CANONICAL)
        decision = decision_for(model)
        aliases = [entry_at(model, path) for path in ('Archive/reference.txt', 'Archive/reference-alias.txt')]
        decision['member_paths'] = [{'entry_id': e['id'], 'project_path': e['relative_path']} for e in aliases]
        result = draft(model, decision)
        self.assertEqual(len(result['members']), 2)
        self.assertEqual(result['capacity']['known_recorded_path_logical_bytes'], sum(e['logical_bytes'] for e in aliases))
        self.assertIn('link_identity_unresolved', codes(result))
        self.assert_incomplete(result)

    def test_verified_hash_stays_recorded_evidence_not_version_or_keep_current(self):
        result = draft(copy.deepcopy(CANONICAL))
        self.assertEqual(result['members'][0]['observation']['hash']['status'], 'verified')
        self.assertEqual(result['members'][0]['placement'], 'current_address_requires_identity')
        self.assert_incomplete(result)

    def test_real_missing_or_truthy_synthetic_flags_are_rejected_without_conversion(self):
        for flag in (False, None, 1, 'true', 'missing'):
            model = copy.deepcopy(CANONICAL)
            if flag == 'missing':
                model.pop('synthetic')
            else:
                model['synthetic'] = flag
            before = copy.deepcopy(model)
            with self.subTest(flag=flag), self.assertRaises(AdapterError):
                observation_digest(model)
            self.assertEqual(model, before)

    def test_partial_cancelled_and_missing_members_remain_uncertain(self):
        for status in ('partial', 'cancelled'):
            model = copy.deepcopy(CANONICAL)
            model['scan']['status'] = status
            model['scan']['coverage']['stop_reason'] = 'cancelled' if status == 'cancelled' else None
            model['changes']['unverified_absent'] = ['historical_missing_member']
            result = draft(model)
            self.assertEqual(result['observation_scope']['reported_changes']['unverified_absent'], ['historical_missing_member'])
            self.assertEqual(result['observation_scope']['reported_changes']['no_longer_observed'], [])
            self.assertIn('observation_scope_incomplete', codes(result))
            self.assertEqual(result['observation_scope']['scan']['status'], status)
            self.assert_incomplete(result)

    def test_complete_bounded_scan_still_does_not_prove_whole_drive_or_backups(self):
        model = copy.deepcopy(CANONICAL)
        model['entries'] = [e for e in model['entries'] if e['status'] == 'observed']
        model['scan'].update(status='complete', errors=[], exclusions=[])
        refresh(model)
        result = draft(model)
        self.assertNotIn('observation_scope_incomplete', codes(result))
        self.assertEqual(result['observation_scope']['scan']['limits'], model['scan']['limits'])
        self.assert_incomplete(result)

    def test_unvisited_destination_is_not_an_empty_online_drive(self):
        model = copy.deepcopy(CANONICAL)
        model['scan']['roots'].append({'id': 'offline_shelf', 'path': '/synthetic/offline-shelf', 'status': 'unvisited', 'identity': None})
        decision = decision_for(model)
        decision['destination_root_id'] = 'offline_shelf'
        result = draft(model, decision)
        self.assertIn('root_not_observed', codes(result))
        root = next(r for r in result['observed_roots'] if r['id'] == 'offline_shelf')
        self.assertEqual(root['status'], 'unvisited')
        self.assertIsNone(root['identity'])
        self.assert_incomplete(result)

    def test_freshness_uses_explicit_clock_and_preserves_old_member_timestamps(self):
        model = copy.deepcopy(CANONICAL)
        for now, state in [('2026-10-06T11:59:59Z', 'future'), ('2026-10-06T14:00:01Z', 'stale'), ('2026-10-06T14:00:00Z', 'within_requested_window')]:
            with self.subTest(now=now):
                result = draft(model, now=now)
                self.assertEqual(result['recorded_scan_freshness'], state)
                self.assertEqual(result['members'][0]['observation']['mtime_ns'], entry_at(model)['mtime_ns'])
                self.assert_incomplete(result)

    def test_changed_snapshot_invalidates_expected_reference(self):
        model = copy.deepcopy(CANONICAL)
        old = observation_digest(model)
        model['scan']['uncertainties'].append('Later declared uncertainty')
        with self.assertRaisesRegex(AdapterError, 'Stale observation'):
            build_observation_draft(model, decision_for(model), expected_observation_digest=old, now=NOW)

    def test_unsupported_and_placeholder_states_are_not_hydrated_or_omitted(self):
        for kind, status, hash_status in [('symlink', 'unsupported', 'disabled'), ('special', 'unsupported', 'disabled'),
                                        ('unknown', 'unreadable', 'disabled'), ('file', 'unsupported', 'placeholder_not_read'),
                                        ('file', 'stale', 'stale'), ('file', 'excluded', 'disabled')]:
            model = copy.deepcopy(CANONICAL)
            entry = entry_at(model)
            entry.update(kind=kind, status=status)
            entry['hash'] = {'status': hash_status, 'algorithm': None, 'value': None}
            entry['uncertainties'].append('Synthetic content uncertainty')
            refresh(model)
            with self.subTest(kind=kind, status=status):
                result = draft(model)
                self.assertEqual(len(result['members']), 1)
                self.assertEqual(result['members'][0]['observation'], entry)
                self.assertIn('member_not_observed', codes(result))
                if hash_status == 'placeholder_not_read':
                    self.assertIn('placeholder_content_unavailable', codes(result))
                self.assert_incomplete(result)

    def test_unknown_size_remains_unknown_and_noop_capacity_is_never_invented(self):
        model = copy.deepcopy(CANONICAL)
        entry = entry_at(model, 'unclassified/not-readable.data')
        decision = decision_for(model)
        decision['member_paths'] = [{'entry_id': entry['id'], 'project_path': 'not-readable.data'}]
        result = draft(model, decision)
        self.assertEqual(result['capacity']['unknown_size_member_ids'], [entry['id']])
        self.assertEqual(result['capacity']['known_recorded_path_logical_bytes'], 0)
        self.assert_incomplete(result)

    def test_directory_selection_never_expands_membership_or_invents_bytes(self):
        model = copy.deepcopy(CANONICAL)
        entry = entry_at(model, 'Project Aurora')
        decision = decision_for(model)
        decision['member_paths'] = [{'entry_id': entry['id'], 'project_path': 'Project Aurora'}]
        result = draft(model, decision)
        self.assertEqual(result['member_ids'], [entry['id']])
        self.assertIn('unsupported_member_kind', codes(result))
        self.assert_incomplete(result)

    def test_project_hypotheses_never_supply_membership_or_dependencies(self):
        model = copy.deepcopy(CANONICAL)
        decision = decision_for(model)
        original = draft(model, decision)
        for directory in model['directories']:
            directory['role_hypotheses'] = []
        model['findings'] = []
        model['relationships'] = []
        model['plan_alternatives'] = []
        updated = draft(model, decision)
        self.assertEqual(updated['members'], original['members'])
        self.assertEqual(updated['member_ids'], original['member_ids'])
        self.assert_incomplete(updated)

    def test_declared_target_collisions_and_occupied_directories_stay_visible(self):
        model = copy.deepcopy(CANONICAL)
        decision = decision_for(model)
        second = entry_at(model, 'Project Aurora/design_v2.blend')
        for path in ('design_v1.blend', 'design_v1.blend/child'):
            decision['member_paths'].append({'entry_id': second['id'], 'project_path': path})
            result = draft(model, decision)
            self.assertIn('declared_project_path_collision', codes(result))
            self.assertIn('observed_target_path_overlap', codes(result))
            decision['member_paths'].pop()
        decision['destination_folder'] = 'Project'
        decision['member_paths'][0]['project_path'] = 'Aurora'
        # This different address is not silently equated with "Project Aurora".
        self.assertNotIn('observed_target_path_overlap', codes(draft(model, decision)))
        decision['destination_folder'] = 'Project Aurora'
        decision['member_paths'][0]['project_path'] = 'new.txt'
        self.assertNotIn('observed_target_path_overlap', codes(draft(model, decision)))
        decision['destination_folder'] = 'Archive'
        decision['member_paths'][0]['project_path'] = 'reference.txt'
        self.assertIn('observed_target_path_overlap', codes(draft(model, decision)))

    def test_case_and_unicode_spelling_never_become_known_name_semantics(self):
        for folder in ('PROJECT AURORA', 'Project Café', 'Project Cafe\u0301'):
            model = copy.deepcopy(CANONICAL)
            decision = decision_for(model)
            decision['destination_folder'] = folder
            result = draft(model, decision)
            self.assertEqual(result['members'][0]['placement'], 'proposed_address_requires_review')
            self.assertIn('volume_name_semantics_unknown', codes(result))
            self.assert_incomplete(result)

    def test_alias_conflicts_reject_in_both_orders(self):
        for field, value in [('logical_bytes', 999), ('allocated_bytes', 999), ('link_count', 9),
                             ('fingerprint', None), ('hash', {'status': 'verified', 'algorithm': 'sha256', 'value': 'f' * 64})]:
            for reverse in (False, True):
                model = copy.deepcopy(CANONICAL)
                entry_at(model, 'Archive/reference-alias.txt')[field] = value
                if reverse:
                    model['entries'].reverse()
                with self.subTest(field=field, reverse=reverse), self.assertRaises(AdapterError):
                    observation_digest(model)

    def test_structural_coverage_and_hash_contradictions_reject(self):
        mutations = [
            lambda m: m['entries'].append(copy.deepcopy(m['entries'][0])),
            lambda m: entry_at(m).__setitem__('parent_id', None),
            lambda m: entry_at(m).__setitem__('root_id', 'unknown-root'),
            lambda m: entry_at(m).__setitem__('relative_path', 'Project Aurora/../escape'),
            lambda m: entry_at(m).__setitem__('status', 'stale'),
            lambda m: m['scan']['coverage'].__setitem__('entries_observed', 999),
            lambda m: m['scan']['coverage'].__setitem__('status_counts', {}),
            lambda m: m['scan']['coverage'].__setitem__('hash_status_counts', {}),
            lambda m: m['scan']['coverage'].__setitem__('hashed_files', 999),
            lambda m: m['scan']['coverage'].__setitem__('complete_within_policy', True),
            lambda m: m['scan'].__setitem__('status', 'complete'),
            lambda m: m['scan'].__setitem__('status', 'cancelled'),
            lambda m: m['scan']['roots'][0]['identity'].__setitem__('inode', 999),
            lambda m: m['scan']['roots'][0].__setitem__('status', 'stale'),
            lambda m: m.__setitem__('read_only', False),
            lambda m: m.__setitem__('executable', True),
        ]
        for mutation in mutations:
            model = copy.deepcopy(CANONICAL)
            mutation(model)
            with self.subTest(mutation=mutations.index(mutation)), self.assertRaises(AdapterError):
                observation_digest(model)

    def test_decision_shape_members_paths_and_authority_fields_are_strict(self):
        model = copy.deepcopy(CANONICAL)
        mutations = [
            lambda d: d.__setitem__('member_paths', []),
            lambda d: d.__setitem__('member_paths', 'all'),
            lambda d: d['member_paths'].append(copy.deepcopy(d['member_paths'][0])),
            lambda d: d['member_paths'][0].__setitem__('entry_id', 'unknown'),
            lambda d: d['member_paths'][0].__setitem__('entry_id', []),
            lambda d: d.__setitem__('destination_root_id', 'unknown'),
            lambda d: d.__setitem__('destination_root_id', []),
            lambda d: d.__setitem__('project_label', ''),
            lambda d: d.__setitem__('acknowledged', 1),
            *[lambda d, key=key: d.__setitem__(key, True) for key in ('execute', 'volume_id', 'backups', 'dependencies', 'synthetic')],
        ]
        for mutation in mutations:
            decision = decision_for(model)
            mutation(decision)
            with self.subTest(mutation=mutations.index(mutation)), self.assertRaises(AdapterError):
                draft(model, decision)
        for path in ('', '../parent', '/absolute', 'C:/drive', 'a\\b', 'a//b', 'a/./b', 'a\nb'):
            for field in ('destination_folder', 'project_path'):
                decision = decision_for(model)
                if field == 'project_path':
                    decision['member_paths'][0][field] = path
                else:
                    decision[field] = path
                with self.subTest(path=path, field=field), self.assertRaises(AdapterError):
                    draft(model, decision)

    def test_unacknowledged_intent_stays_blocked(self):
        model = copy.deepcopy(CANONICAL)
        decision = decision_for(model)
        decision['acknowledged'] = False
        self.assertIn('membership_and_destination_need_review', codes(draft(model, decision)))

    def test_age_bound_and_clock_types_are_strict(self):
        for hours in (0, -1, True, None, '2', 1.5, 8761):
            with self.subTest(hours=hours), self.assertRaises(AdapterError):
                draft(copy.deepcopy(CANONICAL), max_observation_age_hours=hours)
        for now in (None, 0, '2026-10-07', 'invalid'):
            with self.subTest(now=now), self.assertRaises(AdapterError):
                draft(copy.deepcopy(CANONICAL), now=now)

    def test_non_json_deep_nonfinite_and_oversized_inputs_reject(self):
        values = [float('nan'), float('inf'), object(), ('tuple',), 'x' * 4097, 2**63]
        for value in values:
            model = copy.deepcopy(CANONICAL)
            model['arbitrary'] = value
            with self.subTest(kind=type(value).__name__), self.assertRaises(AdapterError):
                observation_digest(model)
        model = copy.deepcopy(CANONICAL)
        model['entries'] = model['entries'] * 126
        with self.assertRaises(AdapterError):
            observation_digest(model)
        model = copy.deepcopy(CANONICAL)
        deep = []
        for _ in range(40):
            deep = [deep]
        model['arbitrary'] = deep
        with self.assertRaises(AdapterError):
            observation_digest(model)
        model['arbitrary'] = [None] * 100001
        with self.assertRaises(AdapterError):
            observation_digest(model)

    def test_oversized_valid_timestamp_fraction_is_rejected(self):
        model = copy.deepcopy(CANONICAL)
        now = '2026-10-06T12:00:00.' + '0' * 5000 + 'Z'
        with self.assertRaises(AdapterError):
            draft(model, now=now)

    def test_partial_or_incomparable_observations_cannot_report_established_absence(self):
        for field, values in [('no_longer_observed', ['historical-missing']),
                              ('unverified_absent', [entry_at(CANONICAL)['id']]),
                              ('changed', [entry_at(CANONICAL)['id']])]:
            model = copy.deepcopy(CANONICAL)
            model['changes'][field] = values
            with self.subTest(field=field), self.assertRaises(AdapterError):
                observation_digest(model)
        model = copy.deepcopy(CANONICAL)
        model['entries'] = [e for e in model['entries'] if e['status'] == 'observed']
        model['scan'].update(status='complete', errors=[], exclusions=[])
        refresh(model)
        model['changes']['no_longer_observed'] = ['historical-missing']
        with self.assertRaises(AdapterError):
            observation_digest(model)

    def test_dense_collision_details_reject_at_issue_budget(self):
        model, decision = dense_case(200)
        validate_inventory(model)
        with self.assertRaisesRegex(AdapterError, 'issue budget'):
            draft(model, decision)

    def test_within_budget_collision_details_are_complete_and_unique(self):
        model, decision = dense_case(20)
        result = draft(model, decision)
        collisions = [issue for issue in result['blockers'] if issue['code'] == 'declared_project_path_collision']
        self.assertEqual(len(collisions), 20 * 19 // 2)
        self.assertEqual(len({tuple(issue['member_ids']) for issue in collisions}), len(collisions))
        self.assert_incomplete(result)

    def test_compact_noncolliding_scope_of_500_members_is_supported(self):
        model, decision = dense_case(500)
        for number, member in enumerate(decision['member_paths']):
            member['project_path'] = f'member{number}'
        result = draft(model, decision)
        self.assertEqual(len(result['members']), 500)
        self.assertNotIn('declared_project_path_collision', codes(result))
        self.assertNotIn('observed_target_path_overlap', codes(result))
        self.assert_incomplete(result)

    def test_large_collision_work_rejects_before_comparisons(self):
        model, decision = dense_case(1000)
        validate_inventory(model)
        with patch('observation_adapter._overlap', side_effect=AssertionError('budget should reject first')):
            with self.assertRaisesRegex(AdapterError, 'collision-comparison budget'):
                draft(model, decision)

    def test_combined_intended_path_is_bounded(self):
        model = copy.deepcopy(CANONICAL)
        decision = decision_for(model)
        decision['destination_folder'] = 'x' * 3000
        decision['member_paths'][0]['project_path'] = 'y' * 3000
        with self.assertRaises(AdapterError):
            draft(model, decision)

    def test_oversized_repeated_text_rejects_before_whole_document_serialisation(self):
        for text, count in [('x' * 4096, 1100), ('\U0001f9ed' * 4096, 100)]:
            model = copy.deepcopy(CANONICAL)
            model['oversized_test_data'] = [text] * count
            original_dumps = json.dumps

            def guarded_dumps(value, *args, **kwargs):
                if value is model:
                    raise AssertionError('Oversized document reached whole-document serialisation')
                return original_dumps(value, *args, **kwargs)

            with self.subTest(escaped=text.startswith('\U0001f9ed')):
                with patch('observation_adapter.json.dumps', side_effect=guarded_dumps):
                    with self.assertRaises(AdapterError):
                        observation_digest(model)

    def test_exact_canonical_byte_boundary_includes_json_escapes(self):
        model = copy.deepcopy(CANONICAL)
        model['scan']['uncertainties'].append('Escaped \n \t " \\ \U0001f9ed')
        encoded = json.dumps(model, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')
        with patch('observation_adapter.MAX_JSON_BYTES', len(encoded)):
            self.assertEqual(len(observation_digest(model)), 64)
        with patch('observation_adapter.MAX_JSON_BYTES', len(encoded) - 1):
            with self.assertRaises(AdapterError):
                observation_digest(model)

    def test_decision_byte_budget_rejects_before_whole_document_serialisation(self):
        model = copy.deepcopy(CANONICAL)
        decision = decision_for(model)
        decision['oversized_test_data'] = ['x' * 4096] * 1100
        expected = observation_digest(model)
        original_dumps = json.dumps

        def guarded_dumps(value, *args, **kwargs):
            if value is decision:
                raise AssertionError('Oversized decision reached whole-document serialisation')
            return original_dumps(value, *args, **kwargs)

        with patch('observation_adapter.json.dumps', side_effect=guarded_dumps):
            with self.assertRaises(AdapterError):
                build_observation_draft(model, decision, expected_observation_digest=expected, now=NOW)

    def test_renderable_text_stays_text_data(self):
        model = copy.deepcopy(CANONICAL)
        decision = decision_for(model)
        decision['project_label'] = '<img src=x onerror=alert(1)>'
        result = draft(model, decision)
        self.assertEqual(result['project']['label'], decision['project_label'])
        self.assert_incomplete(result)

    def test_missing_root_identity_and_unhashed_content_remain_missing(self):
        model = copy.deepcopy(CANONICAL)
        model['scan']['roots'][0]['identity'] = None
        entry_at(model)['hash'] = {'status': 'disabled', 'algorithm': None, 'value': None}
        refresh(model)
        result = draft(model)
        self.assertIsNone(result['observed_roots'][0]['identity'])
        self.assertEqual(result['members'][0]['observation']['hash']['status'], 'disabled')
        self.assert_incomplete(result)

    def test_existing_nested_directory_is_an_occupied_exact_target(self):
        model = copy.deepcopy(CANONICAL)
        directory = copy.deepcopy(entry_at(model, 'Project Aurora'))
        directory.update(id='entry_nested_directory', relative_path='Project Aurora/Render',
                         parent_id=entry_at(model, 'Project Aurora')['id'], object_id=None, fingerprint=None)
        model['entries'].append(directory)
        refresh(model)
        decision = decision_for(model)
        decision['member_paths'][0]['project_path'] = 'Render'
        result = draft(model, decision)
        self.assertIn({'code': 'observed_target_path_overlap',
                       'member_ids': sorted([entry_at(model)['id'], 'entry_nested_directory']),
                       'root_ids': [directory['root_id']]}, result['blockers'])
        self.assert_incomplete(result)

    def test_member_order_does_not_change_scope_or_capacity(self):
        model = multi_root()
        decision = decision_for(model)
        second = entry_at(model, root='root_synthetic_archive')
        decision['member_paths'].append({'entry_id': second['id'], 'project_path': 'Other/design.blend'})
        first = draft(model, decision)
        decision['member_paths'].reverse()
        second = draft(model, decision)
        for field in ('members', 'member_ids', 'capacity', 'blockers', 'protection'):
            self.assertEqual(first[field], second[field])
        self.assertNotEqual(first['decision_digest'], second['decision_digest'])

    def test_unused_export_totals_never_supply_copy_capacity(self):
        model = copy.deepcopy(CANONICAL)
        original = draft(model)
        model['aggregates']['logical_bytes_by_path'] = 999999999
        model['aggregates']['known_allocated_bytes_by_observed_object'] = 0
        result = draft(model)
        self.assertEqual(result['capacity'], original['capacity'])
        self.assertEqual(result['members'], original['members'])
        self.assert_incomplete(result)

    def test_zero_length_and_large_recorded_sizes_never_supply_required_capacity(self):
        for size in (0, 2**60):
            model = copy.deepcopy(CANONICAL)
            entry = entry_at(model)
            entry['logical_bytes'] = size
            entry['fingerprint']['size'] = size
            entry['hash'] = {'status': 'disabled', 'algorithm': None, 'value': None}
            refresh(model)
            result = draft(model)
            self.assertEqual(result['capacity']['known_recorded_path_logical_bytes'], size)
            self.assert_incomplete(result)

    def test_no_mutation_io_scanning_or_planner_execution(self):
        model = multi_root()
        decision = decision_for(model)
        before = copy.deepcopy((model, decision))
        expected = observation_digest(model)
        with patch('builtins.open', side_effect=AssertionError('unexpected file I/O')), \
             patch('socket.socket', side_effect=AssertionError('unexpected socket')), \
             patch('os.open', side_effect=AssertionError('unexpected path access')), \
             patch('os.stat', side_effect=AssertionError('unexpected path access')), \
             patch('os.scandir', side_effect=AssertionError('unexpected scan')), \
             patch('backend.disk_model.scan_storage', side_effect=AssertionError('unexpected scan')), \
             patch('planning_preview.review', side_effect=AssertionError('unexpected planner conversion')):
            first = build_observation_draft(model, decision, expected_observation_digest=expected, now=NOW)
            second = build_observation_draft(model, decision, expected_observation_digest=expected, now=NOW)
        self.assertEqual(first, second)
        self.assertEqual((model, decision), before)
        first['members'][0]['observation']['relative_path'] = 'changed output'
        self.assertEqual((model, decision), before)
        self.assertFalse(any(name in sys.modules for name in ('backend.app', 'backend.guided', 'backend.op_store')))


if __name__ == '__main__':
    unittest.main()
