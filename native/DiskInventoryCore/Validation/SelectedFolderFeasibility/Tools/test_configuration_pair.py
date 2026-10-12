"""Synthetic memory-only pairs: no Xcode parser, file read or host execution."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import unittest
from unittest.mock import patch

import configuration_pair as cp
import probe_contract as pc


RAW = b"synthetic opaque configuration; deliberately not a property list"


def encoded(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode()


def example():
    return {
        "schemaVersion": 1, "rawFormat": "opaque-xctestrun", "sourceCommit": "a" * 40,
        "fixtureRunID": "11111111-1111-4111-8111-111111111111",
        "fixtureCaseID": "22222222-2222-4222-8222-222222222222",
        "fixtureClaimSHA256": "b" * 64, "configurationName": "Owned synthetic case",
        "configurationEnabled": True,
        "toolchain": {"xcodeVersion": "synthetic-version", "xcodeBuild": "synthetic-build",
                      "sdkVersion": "synthetic-sdk", "swiftVersion": "synthetic-swift"},
        "destination": "synthetic owned runner",
        "products": {
            "host": {"path": "Debug/Host.app", "bundleIdentifier": "org.example.host", "inventorySHA256": "c" * 64},
            "runner": {"path": "Debug/Runner.app", "bundleIdentifier": "org.example.runner", "inventorySHA256": "d" * 64},
            "testBundle": {"path": "Debug/Runner.app/PlugIns/Probe.xctest", "bundleIdentifier": "org.example.tests", "inventorySHA256": "e" * 64},
        },
        "launchArguments": ["synthetic-first", "synthetic-second"],
        "launchEnvironment": {"SYNTHETIC_FIXTURE": "claim-only"},
        "testingEnvironment": {"SYNTHETIC_TEST": "claim-only"},
        "enabledTests": ["OwnedTests/Probe/testFirst", "OwnedTests/Probe/testSecond"],
        "skippedTests": [],
        "instrumentation": {key: False for key in sorted(cp.INSTRUMENTATION)},
    }


class ConfigurationPairTests(unittest.TestCase):
    def setUp(self):
        self.value = example()
        self.data = encoded(self.value)
        self.expected = cp.capture_configuration_pair(RAW, self.data)
        self.assertIsNone(cp.require_same_configuration_pair(self.expected, RAW, self.data))

    def reject_changed(self, value):
        data = encoded(value)
        # A valid candidate must first pass schema admission; the mismatch
        # cannot succeed merely because a malformed candidate was rejected.
        cp.capture_configuration_pair(RAW, data)
        with self.assertRaisesRegex(pc.Refusal, "^resolved configuration changed$"):
            cp.require_same_configuration_pair(self.expected, RAW, data)

    def test_exact_pair_is_immutable_and_success_returns_no_permit(self):
        self.assertEqual(self.expected.raw_configuration, RAW)
        self.assertEqual(self.expected.resolved_claim, self.data)
        with self.assertRaises(FrozenInstanceError):
            self.expected.raw_configuration = b"other"
        self.value["launchEnvironment"]["SYNTHETIC_FIXTURE"] = "later mutation"
        self.assertEqual(self.expected.resolved_claim, self.data)

    def test_opaque_non_plist_bytes_do_not_prove_parser_or_semantic_agreement(self):
        other = cp.capture_configuration_pair(b"\xff\0not-plist", self.data)
        self.assertIsNone(cp.require_same_configuration_pair(other, b"\xff\0not-plist", self.data))
        # This accepted consistency result makes no claim of raw/JSON congruence.

    def test_changed_raw_with_unchanged_resolved_claim_refuses(self):
        with self.assertRaisesRegex(pc.Refusal, "^raw configuration changed$"):
            cp.require_same_configuration_pair(self.expected, RAW + b" ", self.data)

    def test_changed_both_sides_refuses_against_separate_expected_pair(self):
        value = deepcopy(self.value); value["configurationName"] = "new"
        with self.assertRaisesRegex(pc.Refusal, "^raw configuration changed$"):
            cp.require_same_configuration_pair(self.expected, RAW + b"new", encoded(value))

    def test_every_identity_destination_and_configuration_scalar_is_bound(self):
        mutations = {"sourceCommit": "f" * 40,
                     "fixtureRunID": "33333333-3333-4333-8333-333333333333",
                     "fixtureCaseID": "44444444-4444-4444-8444-444444444444",
                     "fixtureClaimSHA256": "0" * 64, "configurationName": "Different",
                     "configurationEnabled": False, "destination": "other synthetic runner"}
        for key, replacement in mutations.items():
            with self.subTest(key=key):
                value = deepcopy(self.value); value[key] = replacement; self.reject_changed(value)

    def test_every_toolchain_field_is_bound(self):
        for key in self.value["toolchain"]:
            with self.subTest(key=key):
                value = deepcopy(self.value); value["toolchain"][key] += "-changed"; self.reject_changed(value)

    def test_all_three_products_all_fields_are_bound_with_same_test_names(self):
        for role in self.value["products"]:
            for key in ("path", "bundleIdentifier", "inventorySHA256"):
                with self.subTest(role=role, key=key):
                    value = deepcopy(self.value)
                    value["products"][role][key] = "f" * 64 if key == "inventorySHA256" else value["products"][role][key] + "-other"
                    self.assertEqual(value["enabledTests"], self.value["enabledTests"])
                    self.reject_changed(value)

    def test_both_environments_all_keys_and_values_are_bound(self):
        for field in ("launchEnvironment", "testingEnvironment"):
            for kind in ("value", "added", "removed", "renamed"):
                with self.subTest(field=field, kind=kind):
                    value = deepcopy(self.value); env = value[field]; key = next(iter(env))
                    if kind == "value": env[key] = "changed"
                    elif kind == "added": env["NEW_VARIABLE"] = "additional"
                    elif kind == "removed": env.pop(key)
                    else: env["RENAMED_VARIABLE"] = env.pop(key)
                    self.reject_changed(value)

    def test_arguments_values_order_and_empty_value_are_bound(self):
        for arguments in (["changed", "synthetic-second"], list(reversed(self.value["launchArguments"])), [""], []):
            value = deepcopy(self.value); value["launchArguments"] = arguments; self.reject_changed(value)

    def test_enabled_skipped_and_test_order_are_bound(self):
        for enabled, skipped in ((["OwnedTests/Probe/testOther"], []),
                                  (list(reversed(self.value["enabledTests"])), []),
                                  ([self.value["enabledTests"][0]], [self.value["enabledTests"][1]])):
            value = deepcopy(self.value); value.update(enabledTests=enabled, skippedTests=skipped)
            self.reject_changed(value)

    def test_each_instrumentation_flag_is_bound(self):
        for key in cp.INSTRUMENTATION:
            value = deepcopy(self.value); value["instrumentation"][key] = True; self.reject_changed(value)

    def test_exact_json_bytes_bind_whitespace_and_object_order(self):
        for changed in (json.dumps(self.value, indent=2).encode(), encoded(dict(reversed(list(self.value.items()))))):
            self.assertEqual(json.loads(changed), self.value)
            with self.assertRaisesRegex(pc.Refusal, "^resolved configuration changed$"):
                cp.require_same_configuration_pair(self.expected, RAW, changed)

    def test_unicode_not_normalised(self):
        value = deepcopy(self.value); value["configurationName"] = "é"
        expected = cp.capture_configuration_pair(RAW, encoded(value))
        value["configurationName"] = "e\u0301"
        with self.assertRaisesRegex(pc.Refusal, "^resolved configuration changed$"):
            cp.require_same_configuration_pair(expected, RAW, encoded(value))

    def test_raw_size_and_type_before_resolved_parser(self):
        for invalid in (b"", b"x" * (cp.RAW_BYTES + 1), "text", bytearray(b"bytes")):
            with patch.object(cp, "_validate_resolved", side_effect=AssertionError("parser reached")):
                with self.assertRaisesRegex(pc.Refusal, "^raw configuration byte budget$"):
                    cp.capture_configuration_pair(invalid, self.data)
        cp.capture_configuration_pair(b"x" * cp.RAW_BYTES, self.data)

    def test_resolved_exact_byte_limit_and_overflow(self):
        admitted = self.data + b" " * (cp.RESOLVED_BYTES - len(self.data))
        cp.capture_configuration_pair(RAW, admitted)
        with self.assertRaisesRegex(pc.Refusal, "^JSON byte budget$"):
            cp.capture_configuration_pair(RAW, admitted + b" ")

    def test_malformed_duplicate_unknown_and_nesting_refuse(self):
        for data in (b"\xff", b'{"a":1,"a":2}', b"[" * 17 + b"0" + b"]" * 17,
                     self.data[:-1] + b',"schemaVersion":1}', self.data + b" junk"):
            with self.assertRaises(pc.Refusal): cp.capture_configuration_pair(RAW, data)
        for field in (None, "toolchain", "products", "instrumentation", "products.host"):
            value = deepcopy(self.value)
            target = value if field is None else value["products"]["host"] if field == "products.host" else value[field]
            target["unknown"] = "refuse"
            with self.subTest(field=field), self.assertRaisesRegex(pc.Refusal, "unexpected fields"):
                cp.capture_configuration_pair(RAW, encoded(value))

    def test_missing_fields_wrong_version_and_numeric_boolean_confusion(self):
        for key in cp.ROOT_FIELDS:
            value = deepcopy(self.value); value.pop(key)
            with self.subTest(key=key), self.assertRaises(pc.Refusal): cp.capture_configuration_pair(RAW, encoded(value))
        for key, replacement in (("schemaVersion", True), ("schemaVersion", 2), ("schemaVersion", 1.0), ("configurationEnabled", 1), ("rawFormat", "verified-xctestrun")):
            value = deepcopy(self.value); value[key] = replacement
            with self.assertRaises(pc.Refusal): cp.capture_configuration_pair(RAW, encoded(value))
        value = deepcopy(self.value); value["instrumentation"]["codeCoverage"] = 0
        with self.assertRaisesRegex(pc.Refusal, "instrumentation type"): cp.capture_configuration_pair(RAW, encoded(value))

    def test_expected_constructor_cannot_skip_admission(self):
        for expected in (None, {}, cp.ConfigurationPairClaim(bytearray(b"mutable"), self.data), cp.ConfigurationPairClaim(RAW, b"{}")):
            with self.assertRaises(pc.Refusal): cp.require_same_configuration_pair(expected, RAW, self.data)

    def test_text_byte_limits_types_and_controls(self):
        value = deepcopy(self.value); value["configurationName"] = "é" * 128
        cp.capture_configuration_pair(RAW, encoded(value))
        # The policy excludes ASCII C0/DEL, not every Unicode control category.
        value["configurationName"] = "claim\u0085text"
        c1_data = encoded(value)
        c1_pair = cp.capture_configuration_pair(RAW, c1_data)
        self.assertIsNone(cp.require_same_configuration_pair(c1_pair, RAW, c1_data))
        value["configurationName"] = "claim\u0086text"
        with self.assertRaisesRegex(pc.Refusal, "^resolved configuration changed$"):
            cp.require_same_configuration_pair(c1_pair, RAW, encoded(value))
        for name in ("é" * 129, "", "bad\0name", "bad\nname", "bad\x7fname", "\ud800", True):
            value["configurationName"] = name
            with self.subTest(name=repr(name)), self.assertRaises(pc.Refusal): cp.capture_configuration_pair(RAW, encoded(value))

    def test_sequence_and_environment_count_boundaries(self):
        for field in ("launchArguments", "enabledTests", "skippedTests"):
            value = deepcopy(self.value); value[field] = ["test" + str(i) for i in range(128)]
            cp.capture_configuration_pair(RAW, encoded(value)); value[field].append("extra")
            with self.subTest(field=field), self.assertRaisesRegex(pc.Refusal, "configuration sequence"):
                cp.capture_configuration_pair(RAW, encoded(value))
        for field in ("launchEnvironment", "testingEnvironment"):
            value = deepcopy(self.value); value[field] = {"KEY" + str(i): "" for i in range(128)}
            cp.capture_configuration_pair(RAW, encoded(value)); value[field]["EXTRA"] = ""
            with self.subTest(field=field), self.assertRaisesRegex(pc.Refusal, "configuration environment"):
                cp.capture_configuration_pair(RAW, encoded(value))

    def test_environment_keys_and_values(self):
        for field in ("launchEnvironment", "testingEnvironment"):
            value = deepcopy(self.value); value[field] = {"VALID_KEY": "x" * 4096}
            cp.capture_configuration_pair(RAW, encoded(value))
            for env in ({"INVALID-KEY": ""}, {"1INVALID": ""}, {"X" * 257: ""}, {"VALID_KEY": "x" * 4097}, {"VALID_KEY": 1}):
                value[field] = env
                with self.subTest(field=field, env=list(env)), self.assertRaises(pc.Refusal):
                    cp.capture_configuration_pair(RAW, encoded(value))

    def test_product_paths_claim_digests_and_conflicting_tests(self):
        for path in ("/absolute", "../escape", "a/../b", "a//b", "a/", "a\\b", "", "x" * 1025):
            value = deepcopy(self.value); value["products"]["host"]["path"] = path
            with self.subTest(path=path), self.assertRaises(pc.Refusal): cp.capture_configuration_pair(RAW, encoded(value))
        value = deepcopy(self.value); value["products"]["runner"]["path"] = value["products"]["host"]["path"]
        with self.assertRaisesRegex(pc.Refusal, "distinct product claims"): cp.capture_configuration_pair(RAW, encoded(value))
        for field in ("sourceCommit", "fixtureRunID", "fixtureCaseID", "fixtureClaimSHA256"):
            value = deepcopy(self.value); value[field] = "invalid"
            with self.assertRaises(pc.Refusal): cp.capture_configuration_pair(RAW, encoded(value))
        value = deepcopy(self.value); value["products"]["host"]["inventorySHA256"] = "Z" * 64
        with self.assertRaisesRegex(pc.Refusal, "product digest claim"): cp.capture_configuration_pair(RAW, encoded(value))
        for enabled, skipped in (([], []), (["test", "test"], []), (["test"], ["test"]), ([""], [])):
            value = deepcopy(self.value); value.update(enabledTests=enabled, skippedTests=skipped)
            with self.assertRaises(pc.Refusal): cp.capture_configuration_pair(RAW, encoded(value))


if __name__ == "__main__":
    unittest.main()
