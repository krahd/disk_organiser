import copy
import inspect
import json
import unittest
import unicodedata

import planning_preview
from fixtures import blocked_example, sample_document
from planning_preview import ContractError, digest, loads, review, revise


class PlanningContractTests(unittest.TestCase):
    def setUp(self):
        self.document = sample_document()

    def codes(self):
        return {item["code"] for item in review(self.document)["blockers"]}

    def test_good_fixture_is_reviewable_never_executable(self):
        output = review(self.document)
        self.assertEqual(output["status"], "reviewable_proposal_only")
        for key in ("executable", "undo_available", "source_safe_to_erase"):
            self.assertIs(output[key], False)
        self.assertIsNone(output["execution_authority"])
        self.assertFalse(output["protection"]["live_backup_verified"])
        self.assertFalse(output["protection"]["live_restore_verified"])

    def test_project_structure_and_originals_preserved_in_proposal(self):
        output = review(self.document)
        media = next(item for item in output["proposed_changes"] if item["member_id"] == "media")
        self.assertEqual(media["destination"]["relative_path"], "Client projects/Harbour/Media/clip.mov")
        self.assertTrue(all(item["source_retained"] for item in output["proposed_changes"]))
        self.assertEqual(output["capacity"]["reclaimed_bytes"], 0)
        self.assertEqual(output["capacity"]["required_destination_bytes"], 76_005_000)

    def test_review_is_deterministic_and_does_not_modify_input(self):
        before = copy.deepcopy(self.document)
        self.assertEqual(review(self.document), review(self.document))
        self.assertEqual(before, self.document)

    def test_corrections_are_explicit_and_invalidate_revision(self):
        updated = revise(self.document, expected_digest=digest(self.document), member_ids=["edit", "media", "notes", "extra"],
                         destination_volume_id="archive", destination_folder="Finished/Harbour", acknowledged=True)
        output = review(updated)
        self.assertEqual(output["revision"], 2)
        self.assertEqual(output["membership_corrections"], {"added": ["extra"], "removed": []})
        self.assertNotEqual(output["input_digest"], digest(self.document))
        self.assertIn("verified_independent_copy_requirement_unmet", {item["code"] for item in output["blockers"]})
        self.assertEqual(self.document["revision"], 1)

    def test_stale_edit_rejected(self):
        with self.assertRaises(ContractError):
            revise(self.document, expected_digest="old", member_ids=["edit"], destination_volume_id="archive",
                   destination_folder="Changed", acknowledged=True)

    def test_removed_dependency_blocks_and_is_visible(self):
        self.document["decision"]["member_ids"].remove("media")
        self.assertIn("project_dependency_not_selected", self.codes())
        self.assertEqual(review(self.document)["membership_corrections"]["removed"], ["media"])

    def test_unobserved_dependency_blocks(self):
        self.document["entries"][0]["dependencies"].append("unobserved-asset")
        self.assertIn("project_dependency_not_selected", self.codes())

    def test_unknown_dependency_scope_blocks(self):
        self.document["entries"][0]["dependency_coverage"] = "unknown"
        self.assertIn("project_dependencies_unknown", self.codes())

    def test_user_review_required(self):
        self.document["decision"]["acknowledged"] = False
        self.assertIn("membership_and_destination_need_review", self.codes())

    def test_offline_source_is_not_missing_or_deleted(self):
        self.document["entries"][1]["volume_id"] = "shelf"
        self.assertIn("source_not_online", self.codes())
        self.assertEqual(len(review(self.document)["proposed_changes"]), 3)

    def test_offline_destination_blocks(self):
        self.document["decision"]["destination_volume_id"] = "shelf"
        self.assertIn("destination_not_online", self.codes())

    def test_future_and_old_observations_block(self):
        for timestamp in ("2026-10-07T00:00:00Z", "2026-10-01T00:00:00Z"):
            with self.subTest(timestamp=timestamp):
                self.document["entries"][0]["observed_at"] = timestamp
                self.assertIn("source_observation_stale_or_future", self.codes())

    def test_unknown_or_partial_coverage_blocks(self):
        self.document["volumes"][1]["coverage"] = "partial"
        self.assertIn("destination_coverage_incomplete", self.codes())

    def test_placeholder_symlink_bundle_and_unknown_block(self):
        for kind in ("placeholder", "symlink", "bundle", "unknown"):
            with self.subTest(kind=kind):
                self.document["entries"][0]["kind"] = kind
                self.assertIn("unsupported_" + kind, self.codes())

    def test_hardlink_and_unknown_link_count_block(self):
        for count in (2, None):
            with self.subTest(count=count):
                self.document["entries"][0]["link_count"] = count
                self.assertIn("hardlink_or_link_identity_unknown", self.codes())

    def test_same_version_or_duplicate_never_disposable(self):
        self.document["entries"][1]["version"] = self.document["entries"][0]["version"]
        output = review(self.document)
        self.assertEqual(len(output["proposed_changes"]), 3)
        self.assertFalse(output["source_safe_to_erase"])
        self.assertEqual(output["capacity"]["reclaimed_bytes"], 0)

    def test_case_collision_blocks(self):
        self.document["entries"][1]["project_path"] = "EDIT.PROJECT"
        self.assertIn("planned_name_or_ancestor_collision", self.codes())

    def test_unicode_collision_blocks(self):
        self.document["entries"][0]["project_path"] = "café.txt"
        self.document["entries"][1]["project_path"] = "cafe\u0301.txt"
        self.assertIn("planned_name_or_ancestor_collision", self.codes())

    def test_casefold_then_normalise_collisions_at_all_address_boundaries(self):
        pairs = [("\u0390.txt", "\u0399\u0308\u0301.txt"),
                 ("\u0386\u0345\u0300.txt", "\u03ac\u0300\u0345.txt")]
        for first, second, form in [(a, b, form) for a, b in pairs for form in ("NFC", "NFD")]:
            for boundary in ("proposed", "occupied", "source", "source_ancestor"):
                with self.subTest(form=form, boundary=boundary):
                    self.document = sample_document()
                    self.document["volumes"][0]["unicode_normalization"] = form
                    self.document["volumes"][1]["unicode_normalization"] = form
                    if boundary == "source":
                        self.document["entries"][0]["path"] = "Folder/" + first
                        self.document["entries"][1]["path"] = "Folder/" + second
                        with self.assertRaises(ContractError):
                            review(self.document)
                    elif boundary == "source_ancestor":
                        self.document["entries"][0]["path"] = "Folder/" + first
                        self.document["entries"][1]["path"] = "Folder/" + second + "/child.mov"
                        self.assertIn("source_ancestor_not_a_directory", self.codes())
                    elif boundary == "occupied":
                        self.document["entries"][0]["project_path"] = first
                        self.document["entries"][3]["volume_id"] = "archive"
                        self.document["entries"][3]["path"] = "Client projects/Harbour/" + second
                        self.assertIn("occupied_name_or_ancestor_collision", self.codes())
                    else:
                        self.document["entries"][0]["project_path"] = first
                        self.document["entries"][1]["project_path"] = second
                        self.assertIn("planned_name_or_ancestor_collision", self.codes())

    def test_file_parent_collision_blocks(self):
        self.document["entries"][0]["project_path"] = "Media"
        self.assertIn("planned_name_or_ancestor_collision", self.codes())

    def test_existing_destination_collision_blocks(self):
        existing = copy.deepcopy(self.document["entries"][3])
        existing.update(id="existing", volume_id="archive", path="Client projects/Harbour/Media/clip.mov")
        self.document["entries"].append(existing)
        self.assertIn("occupied_name_or_ancestor_collision", self.codes())

    def test_unknown_name_semantics_block(self):
        self.document["volumes"][1]["case_sensitive"] = None
        self.assertIn("destination_name_semantics_unknown", self.codes())

    def test_unknown_source_name_semantics_block(self):
        for field, value in (("case_sensitive", None), ("unicode_normalization", "unknown")):
            with self.subTest(field=field):
                self.document = sample_document()
                self.document["volumes"][0][field] = value
                self.assertIn("source_name_semantics_unknown", self.codes())

    def test_selected_source_beneath_unselected_filelike_ancestor_blocks(self):
        for kind in ("file", "symlink", "bundle", "placeholder", "unknown"):
            with self.subTest(kind=kind):
                self.document = sample_document()
                other = self.document["entries"][3]
                other["path"] = "Projects/Harbour/Media"
                other["kind"] = kind
                self.assertIn("source_ancestor_not_a_directory", self.codes())

    def test_selected_file_ancestor_of_unselected_entry_blocks(self):
        for kind in ("file", "symlink", "placeholder", "bundle", "unknown"):
            with self.subTest(kind=kind):
                self.document = sample_document()
                child = copy.deepcopy(self.document["entries"][3])
                child.update(id="unselected-child", path=self.document["entries"][0]["path"] + "/child", kind=kind)
                self.document["entries"].append(child)
                self.assertIn("source_ancestor_not_a_directory", self.codes())

    def test_nonportable_names_block(self):
        for name in ("CON.txt", "file.", "LPT1", 'bad?name'):
            with self.subTest(name=name):
                self.document["entries"][0]["project_path"] = name
                self.assertIn("nonportable_destination_name", self.codes())

    def test_unknown_and_insufficient_capacity_block(self):
        self.document["volumes"][1]["free_bytes"] = None
        self.assertIn("destination_capacity_unknown", self.codes())
        self.document["volumes"][1]["free_bytes"] = 1
        self.assertIn("insufficient_observed_capacity", self.codes())

    def test_unknown_size_never_becomes_zero(self):
        self.document["entries"][0]["bytes"] = None
        self.assertIn("required_capacity_unknown", self.codes())
        self.assertIsNone(review(self.document)["capacity"]["required_destination_bytes"])

    def test_configuration_and_provider_success_not_verified_content(self):
        for level in ("declared_configuration", "provider_report", "manifest_verified"):
            with self.subTest(level=level):
                self.document["backups"][0]["level"] = level
                self.assertIn("verified_independent_copy_requirement_unmet", self.codes())

    def test_stale_backup_does_not_protect_new_version(self):
        self.document["entries"][0]["version"] = "synthetic-new-edit"
        self.assertIn("verified_independent_copy_requirement_unmet", self.codes())
        self.assertIn("project_restore_evidence_requirement_unmet", self.codes())

    def test_old_and_future_backup_evidence_do_not_count(self):
        for timestamp in ("2026-10-01T00:00:00Z", "2026-10-07T00:00:00Z"):
            self.document["backups"][0]["observed_at"] = timestamp
            self.assertIn("verified_independent_copy_requirement_unmet", self.codes())

    def test_partial_backup_does_not_prove_full_scope(self):
        self.document["backups"][0]["complete"] = False
        self.assertIn("verified_independent_copy_requirement_unmet", self.codes())

    def test_same_disk_is_not_independent_backup(self):
        self.document["targets"][0]["failure_domain"] = "physical-device-working"
        self.assertIn("verified_independent_copy_requirement_unmet", self.codes())

    def test_unknown_domain_is_not_independent_backup(self):
        self.document["targets"][0]["failure_domain"] = None
        self.assertIn("verified_independent_copy_requirement_unmet", self.codes())

    def test_two_snapshots_on_one_target_count_once(self):
        second = copy.deepcopy(self.document["backups"][0])
        second["id"] = "second-snapshot-same-target"
        second["snapshot_id"] = "synthetic-snapshot-2"
        self.document["backups"].append(second)
        self.document["policy"]["required_independent_copies"] = 2
        output = review(self.document)
        self.assertTrue(all(item["independent_fixture_copy_domains"] == 1 for item in output["protection"]["members"]))
        self.assertIn("verified_independent_copy_requirement_unmet", self.codes())

    def test_sync_does_not_become_versioned_backup(self):
        self.document["targets"][0]["kind"] = "sync"
        self.assertIn("verified_independent_copy_requirement_unmet", self.codes())

    def test_newer_incomplete_snapshot_evidence_supersedes_old_success(self):
        older = self.document["backups"][0]
        older["observed_at"] = "2026-10-06T21:00:00Z"
        newer = copy.deepcopy(older)
        newer.update(id="newer-incomplete", observed_at="2026-10-06T21:30:00Z", complete=False)
        self.document["backups"].append(newer)
        self.assertIn("verified_independent_copy_requirement_unmet", self.codes())

    def test_ambiguous_evidence_timestamp_does_not_pick_a_winner(self):
        other = copy.deepcopy(self.document["backups"][0])
        other.update(id="same-time-other", complete=False)
        self.document["backups"].append(other)
        self.assertIn("ambiguous_latest_backup_evidence", self.codes())

    def test_latest_failed_restore_does_not_leave_old_success_green(self):
        self.document["restores"][0]["completed_at"] = "2026-10-06T21:00:00Z"
        newer = copy.deepcopy(self.document["restores"][0])
        newer.update(id="later-failure", completed_at="2026-10-06T21:30:00Z", outcome="failed")
        self.document["restores"].append(newer)
        self.assertIn("unresolved_restore_evidence_requires_attention", self.codes())
        self.assertIn("project_restore_evidence_requirement_unmet", self.codes())

    def test_sample_pass_cannot_resurrect_project_success_after_failure(self):
        original = self.document["restores"][0]
        original["completed_at"] = "2026-10-06T20:00:00Z"
        failed = copy.deepcopy(original)
        failed.update(id="project-failed", completed_at="2026-10-06T21:00:00Z", outcome="failed")
        sample = copy.deepcopy(original)
        sample.update(id="later-sample-pass", completed_at="2026-10-06T21:30:00Z", scope="sample")
        self.document["restores"].extend([failed, sample])
        self.assertIn("project_restore_evidence_requirement_unmet", self.codes())
        full = copy.deepcopy(original)
        full.update(id="fresh-project-pass", completed_at="2026-10-06T21:45:00Z")
        self.document["restores"].append(full)
        self.assertNotIn("project_restore_evidence_requirement_unmet", self.codes())

    def test_bytes_only_pass_does_not_resurrect_application_proof(self):
        original = self.document["restores"][0]
        original["completed_at"] = "2026-10-06T20:00:00Z"
        failed = copy.deepcopy(original)
        failed.update(id="app-failed", completed_at="2026-10-06T21:00:00Z", outcome="failed")
        later_bytes = copy.deepcopy(original)
        later_bytes.update(id="bytes-pass", completed_at="2026-10-06T21:30:00Z", check="bytes")
        self.document["restores"].extend([failed, later_bytes])
        self.assertIn("project_restore_evidence_requirement_unmet", self.codes())
        self.document["policy"]["required_restore_check"] = "bytes"
        self.assertNotIn("project_restore_evidence_requirement_unmet", self.codes())
        output = review(self.document)["protection"]["restore_observations"]
        self.assertFalse(next(item for item in output if item["restore_id"] == original["id"])["satisfies_project_fixture_restore"])

    def test_snapshot_restore_failure_cannot_hide_under_other_evidence_record(self):
        self.document["backups"][0]["observed_at"] = "2026-10-06T19:00:00Z"
        newer_evidence = copy.deepcopy(self.document["backups"][0])
        newer_evidence.update(id="new-evidence-same-snapshot", observed_at="2026-10-06T21:30:00Z")
        self.document["backups"].append(newer_evidence)
        self.document["restores"][0].update(backup_id=newer_evidence["id"], completed_at="2026-10-06T20:00:00Z")
        failure = copy.deepcopy(self.document["restores"][0])
        failure.update(id="failed-via-old-record", backup_id="local-content-evidence", completed_at="2026-10-06T21:00:00Z", outcome="failed")
        self.document["restores"].append(failure)
        self.assertIn("project_restore_evidence_requirement_unmet", self.codes())

    def test_newer_failed_other_snapshot_stays_visible_beside_old_valid_restore(self):
        other_backup = copy.deepcopy(self.document["backups"][0])
        other_backup.update(id="another-backup", snapshot_id="another-snapshot")
        self.document["backups"].append(other_backup)
        failed = copy.deepcopy(self.document["restores"][0])
        failed.update(id="another-snapshot-failed", backup_id="another-backup", outcome="failed")
        self.document["restores"].append(failed)
        result = review(self.document)
        self.assertTrue(result["protection"]["project_restore_satisfied_in_fixture"])
        self.assertIn("unresolved_restore_evidence_requires_attention", self.codes())
        self.assertEqual(result["status"], "blocked_review")
        self.assertTrue(any(item["outcome"] == "failed" for item in result["protection"]["restore_observations"]))

    def test_other_snapshot_failure_survives_later_sample_success(self):
        original = self.document["restores"][0]
        original["completed_at"] = "2026-10-06T20:00:00Z"
        backup = copy.deepcopy(self.document["backups"][0])
        backup.update(id="newer-snapshot", snapshot_id="snapshot-2")
        self.document["backups"].append(backup)
        failed = copy.deepcopy(original)
        failed.update(id="newer-failed", backup_id=backup["id"], completed_at="2026-10-06T21:00:00Z", outcome="failed")
        sample = copy.deepcopy(failed)
        sample.update(id="newer-sample-passed", completed_at="2026-10-06T21:30:00Z", outcome="passed", scope="sample", entry_versions={"edit": "synthetic-v1-edit"})
        self.document["restores"].extend([failed, sample])
        result = review(self.document)
        self.assertTrue(result["protection"]["project_restore_satisfied_in_fixture"])
        self.assertIn("unresolved_restore_evidence_requires_attention", self.codes())
        self.assertEqual(result["protection"]["restore_alerts"][0]["snapshot_id"], "snapshot-2")

    def test_historical_ambiguity_cannot_be_hidden_by_later_sample(self):
        original = self.document["restores"][0]
        original["completed_at"] = "2026-10-06T20:00:00Z"
        tied = copy.deepcopy(original)
        tied.update(id="tied-partial", entry_versions={"edit": "synthetic-v1-edit"})
        sample = copy.deepcopy(tied)
        sample.update(id="later-sample", completed_at="2026-10-06T21:30:00Z", scope="sample")
        self.document["restores"].extend([tied, sample])
        self.assertIn("unresolved_restore_evidence_requires_attention", self.codes())
        self.assertIn("project_restore_evidence_requirement_unmet", self.codes())
        resolved = copy.deepcopy(original)
        resolved.update(id="later-complete", completed_at="2026-10-06T21:45:00Z")
        self.document["restores"].append(resolved)
        self.assertNotIn("unresolved_restore_evidence_requires_attention", self.codes())
        self.assertNotIn("project_restore_evidence_requirement_unmet", self.codes())

    def test_bytes_policy_does_not_dismiss_unresolved_application_failure(self):
        self.test_bytes_only_pass_does_not_resurrect_application_proof()
        self.assertIn("unresolved_restore_evidence_requires_attention", self.codes())

    def test_insufficient_appended_success_never_clears_wider_failure_or_ambiguity(self):
        for problem in ("failed", "unknown", "ambiguous"):
            for later_scope, later_check in (("sample", "bytes"), ("sample", "bytes_and_app"), ("project", "bytes")):
                with self.subTest(problem=problem, scope=later_scope, check=later_check):
                    self.document = sample_document()
                    original = self.document["restores"][0]
                    original["completed_at"] = "2026-10-06T20:00:00Z"
                    bad = copy.deepcopy(original)
                    bad.update(id="bad", completed_at="2026-10-06T21:00:00Z",
                               outcome=problem if problem != "ambiguous" else "passed")
                    self.document["restores"].append(bad)
                    if problem == "ambiguous":
                        tied = copy.deepcopy(bad)
                        tied.update(id="tied", entry_versions={"edit": "synthetic-v1-edit"})
                        self.document["restores"].append(tied)
                    self.assertIn("unresolved_restore_evidence_requires_attention", self.codes())
                    later = copy.deepcopy(original)
                    later.update(id="insufficient-later", completed_at="2026-10-06T21:30:00Z",
                                 scope=later_scope, check=later_check)
                    self.document["restores"].append(later)
                    self.assertIn("unresolved_restore_evidence_requires_attention", self.codes())
                    self.assertIn("project_restore_evidence_requirement_unmet", self.codes())

    def test_canonical_caseless_key_follows_decompose_fold_normalise_rule(self):
        strings = ["\u0386\u0345\u0300", "\u03ac\u0300\u0345", "\u0390", "\u0399\u0308\u0301",
                   "Straße", "STRASSE", "İ", "i\u0307", "café", "cafe\u0301", "ι", "ι"]
        for form in ("NFC", "NFD"):
            volume = {"case_sensitive": False, "unicode_normalization": form}
            for value in strings:
                expected = unicodedata.normalize(form, unicodedata.normalize("NFD", value).casefold())
                self.assertEqual(planning_preview._normalise(value, volume), expected)

    def test_unknown_tied_future_restore_events_cannot_revive_old_success(self):
        for condition in ("unknown", "tied", "future"):
            with self.subTest(condition=condition):
                self.document = sample_document()
                self.document["restores"][0]["completed_at"] = "2026-10-06T20:00:00Z"
                later = copy.deepcopy(self.document["restores"][0])
                later.update(id="later", completed_at="2026-10-06T21:00:00Z")
                if condition == "unknown":
                    later["outcome"] = "unknown"
                elif condition == "future":
                    later["completed_at"] = "2026-10-07T21:00:00Z"
                else:
                    tied = copy.deepcopy(later)
                    tied["id"] = "tied"
                    self.document["restores"].append(tied)
                self.document["restores"].append(later)
                self.assertIn("project_restore_evidence_requirement_unmet", self.codes())

    def test_duplicate_source_addresses_are_rejected(self):
        self.document["entries"][1]["path"] = self.document["entries"][0]["path"].upper()
        with self.assertRaises(ContractError):
            review(self.document)

    def test_sample_restore_never_proves_whole_project(self):
        self.document["restores"][0]["scope"] = "sample"
        self.assertIn("project_restore_evidence_requirement_unmet", self.codes())

    def test_failed_or_stale_restore_not_success(self):
        self.document["restores"][0]["outcome"] = "failed"
        self.assertIn("project_restore_evidence_requirement_unmet", self.codes())
        self.document["restores"][0]["outcome"] = "passed"
        self.document["restores"][0]["completed_at"] = "2026-09-01T00:00:00Z"
        self.assertIn("project_restore_evidence_requirement_unmet", self.codes())

    def test_restore_matching_subset_not_whole_project(self):
        del self.document["restores"][0]["entry_versions"]["media"]
        self.assertIn("project_restore_evidence_requirement_unmet", self.codes())

    def test_real_data_flag_and_unknown_contract_rejected(self):
        for key, value in (("synthetic", False), ("schema_version", "future/v2")):
            document = sample_document()
            document[key] = value
            with self.assertRaises(ContractError):
                review(document)

    def test_unknown_fields_and_duplicate_ids_rejected(self):
        self.document["decision"]["apply"] = True
        with self.assertRaises(ContractError):
            review(self.document)
        self.document = sample_document()
        self.document["entries"].append(copy.deepcopy(self.document["entries"][0]))
        with self.assertRaises(ContractError):
            review(self.document)

    def test_traversing_absolute_or_backslash_paths_rejected(self):
        for path in ("../out", "/root/file", "a/../b", "a//b", "a\\b", "C:drive"):
            with self.subTest(path=path):
                self.document["decision"]["destination_folder"] = path
                with self.assertRaises(ContractError):
                    review(self.document)

    def test_bool_bytes_and_naive_dates_rejected(self):
        self.document["entries"][0]["bytes"] = True
        with self.assertRaises(ContractError):
            review(self.document)
        self.document = sample_document()
        self.document["now"] = "2026-10-06T22:00:00"
        with self.assertRaises(ContractError):
            review(self.document)

    def test_duplicate_json_keys_and_nan_rejected(self):
        for payload in ('{"synthetic": true, "synthetic": false}', '{"a": NaN}'):
            with self.assertRaises(ContractError):
                loads(payload)

    def test_full_json_round_trip(self):
        self.assertEqual(review(loads(json.dumps(self.document))), review(self.document))

    def test_module_has_no_disk_network_or_executor_imports(self):
        source = inspect.getsource(planning_preview)
        for module in ("os", "pathlib", "shutil", "subprocess", "socket", "requests", "guided", "op_store", "fs_ops"):
            self.assertNotIn("import " + module, source)

    def test_blocked_demo_has_useful_next_decisions(self):
        result = review(blocked_example())
        codes = {item["code"] for item in result["blockers"]}
        self.assertTrue({"unsupported_placeholder", "project_dependencies_unknown", "verified_independent_copy_requirement_unmet", "project_restore_evidence_requirement_unmet"} <= codes)


if __name__ == "__main__":
    unittest.main()
