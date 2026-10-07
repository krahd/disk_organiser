"""Synthetic declared keep-current tests. Never touch source/destination files."""

import copy
import unittest
from unittest.mock import patch

from fixtures import sample_document
from planning_preview import review


def current_home():
    document = sample_document()
    document['decision'].update(destination_volume_id='working', destination_folder='Projects/Harbour')
    return document


def codes(result):
    return {item['code'] for item in result['blockers']}


def proposals(result):
    return {item['member_id']: item['proposal'] for item in result['proposed_changes']}


class KeepCurrentTests(unittest.TestCase):
    def assert_safe(self, result):
        self.assertFalse(result['executable'])
        self.assertIsNone(result['execution_authority'])
        self.assertFalse(result['undo_available'])
        self.assertFalse(result['source_safe_to_erase'])
        self.assertFalse(result['protection']['live_backup_verified'])
        self.assertFalse(result['protection']['live_restore_verified'])
        self.assertEqual(result['capacity']['reclaimed_bytes'], 0)
        self.assertIsNone(result['capacity']['physical_allocation_prediction'])

    def test_exact_current_home_is_declared_no_op(self):
        result = review(current_home())
        self.assertEqual(result['status'], 'reviewable_proposal_only')
        self.assertEqual(result['blockers'], [])
        self.assertEqual(set(proposals(result).values()), {'keep_current'})
        for item in result['proposed_changes']:
            self.assertEqual(item['source']['volume_id'], item['destination']['volume_id'])
            self.assertEqual(item['source']['relative_path'], item['destination']['relative_path'])
            self.assertTrue(item['source_retained'])
        for field in ('known_logical_copy_bytes', 'reserve_bytes', 'required_destination_bytes'):
            self.assertEqual(result['capacity'][field], 0)
        self.assert_safe(result)

    def test_no_op_needs_no_copy_space_even_when_free_or_member_bytes_unknown(self):
        for free in (0, None):
            with self.subTest(free=free):
                document = current_home()
                document['volumes'][0]['free_bytes'] = free
                for entry in document['entries']:
                    entry['bytes'] = None
                result = review(document)
                self.assertEqual(result['blockers'], [])
                self.assertEqual(result['capacity']['required_destination_bytes'], 0)
                self.assertEqual(result['capacity']['unknown_size_member_ids'], [])
                self.assertEqual(result['capacity']['observed_free_bytes'], free)
                self.assert_safe(result)

    def test_unproven_current_identity_is_neither_copy_nor_no_op(self):
        mutations = [
            ('volume', 'state', 'offline', 'source_not_online'),
            ('volume', 'state', 'unknown', 'source_not_online'),
            ('volume', 'coverage', 'partial', 'source_coverage_incomplete'),
            ('volume', 'case_sensitive', None, 'source_name_semantics_unknown'),
            ('volume', 'unicode_normalization', 'unknown', 'source_name_semantics_unknown'),
            ('volume', 'observed_at', '2026-10-01T00:00:00Z', 'source_volume_observation_stale_or_future'),
            ('volume', 'observed_at', '2026-10-07T00:00:00Z', 'source_volume_observation_stale_or_future'),
            ('entry', 'observed_at', '2026-10-01T00:00:00Z', 'source_observation_stale_or_future'),
            ('entry', 'observed_at', '2026-10-07T00:00:00Z', 'source_observation_stale_or_future'),
            ('entry', 'version', None, 'source_version_unknown'),
            ('entry', 'link_count', None, 'hardlink_or_link_identity_unknown'),
            ('entry', 'link_count', 2, 'hardlink_or_link_identity_unknown'),
            *[('entry', 'kind', kind, 'unsupported_' + kind) for kind in ('symlink', 'placeholder', 'bundle', 'unknown')],
        ]
        for scope, field, value, expected in mutations:
            with self.subTest(scope=scope, field=field, value=value):
                document = current_home()
                record = document['volumes'][0] if scope == 'volume' else document['entries'][0]
                record[field] = value
                result = review(document)
                self.assertEqual(proposals(result)['edit'], 'unresolved_current_location')
                self.assertTrue({expected, 'current_location_identity_unproven', 'occupied_name_or_ancestor_collision'} <= codes(result))
                self.assertIsNone(result['capacity']['required_destination_bytes'])
                self.assert_safe(result)

    def test_unknown_name_semantics_retain_dependency_layout_uncertainty(self):
        document = current_home()
        document['volumes'][0]['case_sensitive'] = None
        self.assertIn('project_dependency_layout_unknown', codes(review(document)))

    def test_same_labels_or_versions_on_different_volume_are_not_identity(self):
        document = sample_document()
        document['volumes'][1]['label'] = document['volumes'][0]['label']
        document['volumes'][1]['failure_domain'] = document['volumes'][0]['failure_domain']
        document['decision']['destination_folder'] = 'Projects/Harbour'
        result = review(document)
        self.assertEqual(set(proposals(result).values()), {'copy_with_project_structure'})
        self.assertEqual(result['capacity']['known_logical_copy_bytes'], 12005000)
        self.assertEqual(result['capacity']['required_destination_bytes'], 76005000)

    def test_case_only_changed_address_remains_a_collision(self):
        document = current_home()
        document['decision']['destination_folder'] = 'Projects/HARBOUR'
        result = review(document)
        self.assertEqual(set(proposals(result).values()), {'copy_with_project_structure'})
        self.assertIn('occupied_name_or_ancestor_collision', codes(result))
        self.assertGreater(result['capacity']['required_destination_bytes'], 0)

    def test_unicode_equivalent_spelling_is_not_exact_identity(self):
        document = current_home()
        for entry in document['entries']:
            entry['path'] = entry['path'].replace('Harbour', 'Café')
        document['decision']['destination_folder'] = 'Projects/Cafe\u0301'
        result = review(document)
        self.assertEqual(set(proposals(result).values()), {'copy_with_project_structure'})
        self.assertIn('occupied_name_or_ancestor_collision', codes(result))

    def test_mixed_plan_counts_only_copies_plus_one_reserve(self):
        document = current_home()
        document['entries'][2]['project_path'] = 'Notes/renamed.txt'
        result = review(document)
        self.assertEqual(proposals(result), {'edit': 'keep_current', 'media': 'keep_current', 'notes': 'copy_with_project_structure'})
        self.assertEqual(result['capacity']['known_logical_copy_bytes'], 1000)
        self.assertEqual(result['capacity']['required_destination_bytes'], 64001000)
        self.assertIn('project_dependency_layout_requires_review', codes(result))
        self.assertNotIn('occupied_name_or_ancestor_collision', codes(result))
        self.assert_safe(result)

    def test_unknown_copy_size_in_mixed_plan_remains_unknown(self):
        document = current_home()
        document['entries'][2].update(project_path='Notes/renamed.txt', bytes=None)
        result = review(document)
        self.assertIsNone(result['capacity']['required_destination_bytes'])
        self.assertEqual(result['capacity']['unknown_size_member_ids'], ['notes'])
        self.assertIn('required_capacity_unknown', codes(result))

    def test_zero_byte_copy_still_requires_reserve(self):
        document = current_home()
        document['entries'][2].update(project_path='Notes/renamed.txt', bytes=0)
        result = review(document)
        self.assertEqual(result['capacity']['known_logical_copy_bytes'], 0)
        self.assertEqual(result['capacity']['required_destination_bytes'], 64000000)

    def test_unrelated_occupied_target_is_not_excused(self):
        document = current_home()
        document['entries'][2]['project_path'] = 'Exports/delivery.mov'
        result = review(document)
        self.assertEqual(proposals(result)['notes'], 'copy_with_project_structure')
        self.assertIn({'code': 'occupied_name_or_ancestor_collision', 'member_ids': ['extra', 'notes']}, result['blockers'])

    def test_copy_cannot_overlap_a_kept_member(self):
        for target in ('edit.project', 'edit.project/child'):
            with self.subTest(target=target):
                document = current_home()
                document['entries'][2]['project_path'] = target
                result = review(document)
                self.assertEqual(proposals(result)['edit'], 'keep_current')
                self.assertTrue({'planned_name_or_ancestor_collision', 'occupied_name_or_ancestor_collision'} <= codes(result))

    def test_current_source_ancestor_conflict_prevents_identity_proof(self):
        document = current_home()
        document['entries'][3]['path'] = 'Projects/Harbour/Media'
        result = review(document)
        self.assertEqual(proposals(result)['media'], 'unresolved_current_location')
        self.assertTrue({'source_ancestor_not_a_directory', 'occupied_name_or_ancestor_collision', 'current_location_identity_unproven'} <= codes(result))
        self.assertIsNone(result['capacity']['required_destination_bytes'])

    def test_current_child_conflict_prevents_identity_proof(self):
        document = current_home()
        document['entries'][3]['path'] = 'Projects/Harbour/edit.project/child'
        result = review(document)
        self.assertEqual(proposals(result)['edit'], 'unresolved_current_location')
        self.assertIn('source_ancestor_not_a_directory', codes(result))

    def test_no_op_retains_membership_and_dependency_blockers(self):
        document = current_home()
        document['decision']['acknowledged'] = False
        document['decision']['member_ids'].remove('media')
        document['entries'][0]['dependency_coverage'] = 'unknown'
        result = review(document)
        self.assertEqual(set(proposals(result).values()), {'keep_current'})
        self.assertTrue({'membership_and_destination_need_review', 'project_dependency_not_selected', 'project_dependencies_unknown'} <= codes(result))
        self.assertEqual(result['capacity']['required_destination_bytes'], 0)

    def test_no_op_does_not_clear_backup_or_restore_gaps(self):
        document = current_home()
        document['backups'][0]['entry_versions']['edit'] = 'older-version'
        document['restores'][0]['outcome'] = 'failed'
        result = review(document)
        self.assertEqual(set(proposals(result).values()), {'keep_current'})
        self.assertTrue({'verified_independent_copy_requirement_unmet', 'project_restore_evidence_requirement_unmet', 'unresolved_restore_evidence_requires_attention'} <= codes(result))
        self.assert_safe(result)

    def test_ordinary_copy_review_preserves_capacity(self):
        result = review(sample_document())
        self.assertEqual(result['blockers'], [])
        self.assertEqual(set(proposals(result).values()), {'copy_with_project_structure'})
        self.assertEqual(result['capacity']['known_logical_copy_bytes'], 12005000)
        self.assertEqual(result['capacity']['required_destination_bytes'], 76005000)

    def test_deterministic_nonmutating_no_io(self):
        document = current_home()
        original = copy.deepcopy(document)
        with patch('builtins.open', side_effect=AssertionError('unexpected I/O')), patch('socket.socket', side_effect=AssertionError('unexpected network')):
            first = review(document)
            second = review(document)
        self.assertEqual(first, second)
        self.assertEqual(document, original)
        self.assertEqual(set(proposals(first).values()), {'keep_current'})
        self.assert_safe(first)


if __name__ == '__main__':
    unittest.main()
