"""Pure-data regressions: selected dependency IDs do not prove layout fidelity."""

import copy
import unittest
from unittest.mock import patch

from fixtures import sample_document
from planning_preview import review


class DependencyLayoutTests(unittest.TestCase):
    def setUp(self):
        self.document = sample_document()

    def codes(self, result=None):
        return {item["code"] for item in (result or review(self.document))["blockers"]}

    def assert_layout_review(self, members):
        result = review(self.document)
        self.assertEqual(result["status"], "blocked_review")
        self.assertIn({"code": "project_dependency_layout_requires_review", "member_ids": sorted(members)},
                      result["blockers"])
        return result

    def test_renamed_or_reparented_dependency_requires_review(self):
        for path in ("Media/renamed.mov", "Elsewhere/clip.mov", "clip.mov"):
            with self.subTest(path=path):
                self.document["entries"][1]["project_path"] = path
                self.assert_layout_review(["edit", "media"])

    def test_reparented_declaring_member_requires_review(self):
        self.document["entries"][0]["project_path"] = "Edits/edit.project"
        self.assert_layout_review(["edit", "media"])
        self.assert_layout_review(["edit", "notes"])

    def test_parent_relative_dependency_address_is_checked(self):
        self.document["entries"][0].update(path="Projects/Harbour/Edits/edit.project", project_path="Edits/edit.project")
        self.assertEqual(review(self.document)["status"], "reviewable_proposal_only")
        self.document["entries"][1]["project_path"] = "Edits/Media/clip.mov"
        self.assert_layout_review(["edit", "media"])

    def test_different_declared_source_roots_are_not_flattened_silently(self):
        self.document["entries"][1]["path"] = "Other project/Media/clip.mov"
        self.assert_layout_review(["edit", "media"])

    def test_shared_destination_prefix_keeps_the_declared_relative_layout(self):
        for entry in self.document["entries"]:
            entry["project_path"] = "Preserved/" + entry["project_path"]
        self.assertEqual(review(self.document)["status"], "reviewable_proposal_only")

    def test_different_source_volume_keeps_layout_unknown(self):
        self.document["entries"][1]["volume_id"] = "archive"
        result = review(self.document)
        self.assertIn({"code": "project_dependency_layout_unknown", "member_ids": ["edit", "media"]},
                      result["blockers"])
        self.assertEqual(result["status"], "blocked_review")

    def test_equal_volume_labels_do_not_establish_relative_layout(self):
        self.document["volumes"][1]["label"] = self.document["volumes"][0]["label"]
        self.document["entries"][1]["volume_id"] = "archive"
        self.assertIn("project_dependency_layout_unknown", self.codes())

    def test_unknown_source_or_destination_name_semantics_stay_unknown(self):
        for volume_index in (0, 1):
            for field, value in (("case_sensitive", None), ("unicode_normalization", "unknown")):
                with self.subTest(volume=volume_index, field=field):
                    self.document = sample_document()
                    self.document["volumes"][volume_index][field] = value
                    self.assertIn("project_dependency_layout_unknown", self.codes())

    def test_case_and_unicode_spelling_changes_require_review(self):
        for original, proposed in (("Media/clip.mov", "MEDIA/clip.mov"),
                                   ("Media/café.mov", "Media/cafe\u0301.mov")):
            with self.subTest(original=original, proposed=proposed):
                self.document = sample_document()
                self.document["entries"][1]["path"] = "Projects/Harbour/" + original
                self.document["entries"][1]["project_path"] = proposed
                self.assert_layout_review(["edit", "media"])

    def test_missing_dependency_retains_the_existing_membership_blocker(self):
        self.document["decision"]["member_ids"].remove("media")
        self.document["entries"][0]["dependencies"].append("unobserved")
        codes = self.codes()
        self.assertIn("project_dependency_not_selected", codes)
        self.assertNotIn("project_dependency_layout_unknown", codes)
        self.assertNotIn("project_dependency_layout_requires_review", codes)

    def test_unselected_declaring_member_does_not_invent_a_selected_edge(self):
        self.document["decision"]["member_ids"] = ["media", "notes"]
        self.document["entries"][1]["project_path"] = "Elsewhere/renamed.mov"
        self.assertEqual(review(self.document)["status"], "reviewable_proposal_only")

    def test_preserved_cyclic_dependency_layout_is_not_rejected(self):
        self.document["entries"][1]["dependencies"] = ["edit"]
        self.assertEqual(review(self.document)["status"], "reviewable_proposal_only")

    def test_historical_restore_does_not_clear_a_changed_layout_blocker(self):
        self.document["entries"][1]["project_path"] = "Elsewhere/renamed.mov"
        result = self.assert_layout_review(["edit", "media"])
        self.assertTrue(result["protection"]["project_restore_satisfied_in_fixture"])
        self.assertFalse(result["protection"]["live_restore_verified"])
        self.assertFalse(result["protection"]["live_backup_verified"])

    def test_determinism_nonmutation_and_authority_boundaries(self):
        self.document["entries"][1]["project_path"] = "Elsewhere/renamed.mov"
        before = copy.deepcopy(self.document)
        with patch("builtins.open", side_effect=AssertionError("unexpected file access")):
            first = review(self.document)
            second = review(self.document)
        self.assertEqual(first, second)
        self.assertEqual(self.document, before)
        self.assertIsNone(first["execution_authority"])
        for field in ("executable", "undo_available", "source_safe_to_erase"):
            self.assertIs(first[field], False)
        self.assertTrue(all(change["source_retained"] for change in first["proposed_changes"]))
        self.assertEqual(first["capacity"]["reclaimed_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
