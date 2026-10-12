"""Memory-only contract tests; the two reads below load repository-owned examples."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import stat
import unittest
from unittest.mock import patch

import probe_contract as pc


HERE = Path(__file__).parent


def encoded(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode()


def directory(path="."):
    return dict(path=path, kind="directory", mode=stat.S_IFDIR | 0o700, uid=501, gid=20)


def file(path="existing", size=3):
    return dict(path=path, kind="file", mode=stat.S_IFREG | 0o600, uid=501, gid=20,
                size=size, sha256=hashlib.sha256(b"abc").hexdigest())


def link(path="alias", target="existing"):
    return dict(path=path, kind="symlink", mode=stat.S_IFLNK | 0o777, uid=501, gid=20, target=target)


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads((HERE / "fixture-claim.example.json").read_bytes())

    def parse(self):
        return pc.parse_fixture_claim(encoded(self.value))

    def test_valid_description_is_immutable(self):
        value = self.parse()
        self.assertEqual(len(value.objects), 4)
        self.assertEqual(dict(value.paths)["selectedFile"], self.value["selectedFile"])
        with self.assertRaises(FrozenInstanceError):
            value.case_id = "changed"

    def test_unknown_or_missing_fields(self):
        for change in (lambda x: x.update(extra=True), lambda x: x.pop("runID")):
            value = deepcopy(self.value); change(value)
            with self.assertRaises(pc.Refusal):
                pc.parse_fixture_claim(encoded(value))

    def test_version_bool_and_numeric_types(self):
        for version in (True, 1.0, "1", 2):
            self.value["schemaVersion"] = version
            with self.subTest(version=version), self.assertRaises(pc.Refusal):
                self.parse()

    def test_noncanonical_uuid_and_case_binding(self):
        for change in (lambda x: x.update(runID="{11111111-1111-4111-8111-111111111111}"),
                       lambda x: x.update(caseID="22222222-2222-4222-8222-222222222223"),
                       lambda x: x.update(bundleIdentifier="org.other.app")):
            value = deepcopy(self.value); change(value)
            with self.assertRaises(pc.Refusal):
                pc.parse_fixture_claim(encoded(value))

    def test_fixed_coordinates(self):
        for key in ("selectedPath", "selectedFile", "siblingFile", "absentPath"):
            value = deepcopy(self.value); value[key] += "-other"
            with self.subTest(key=key), self.assertRaises(pc.Refusal):
                pc.parse_fixture_claim(encoded(value))

    def test_unsafe_parent_and_derived_length(self):
        for parent in ("/", "relative", "/a/../b", "/a//b", "/a/", "/a\0b", "/a\\b", "/a\ud800", "/" + "x" * 1000):
            value = deepcopy(self.value); value["fixtureParent"] = parent
            value.update(selectedPath=parent + "/selected", selectedFile=parent + "/selected/probe.bin",
                         siblingFile=parent + "/outside/sentinel.bin", absentPath=parent + "/selected/must-remain-absent.bin")
            with self.subTest(parent=repr(parent)), self.assertRaises(pc.Refusal):
                pc.parse_fixture_claim(encoded(value))

    def test_fixed_positive_controls(self):
        for field in ("selectedBytesHex", "siblingBytesHex"):
            value = deepcopy(self.value); value[field] = "00" * 32
            with self.assertRaises(pc.Refusal):
                pc.parse_fixture_claim(encoded(value))

    def test_integer_ranges_reject_bool_and_float(self):
        for field in ("device", "inode", "mode", "uid", "gid", "size"):
            for invalid in (-1, True, 1.0, 2**65):
                value = deepcopy(self.value); value["objects"]["selectedFile"][field] = invalid
                with self.subTest(field=field, invalid=invalid), self.assertRaises(pc.Refusal):
                    pc.parse_fixture_claim(encoded(value))

    def test_modes_and_positive_length(self):
        for field, invalid in (("mode", stat.S_IFLNK | 0o777), ("mode", stat.S_IFREG | 0o666), ("size", 0), ("size", 33)):
            value = deepcopy(self.value); value["objects"]["selectedFile"][field] = invalid
            with self.assertRaises(pc.Refusal):
                pc.parse_fixture_claim(encoded(value))

    def test_duplicate_object_identity(self):
        self.value["objects"]["siblingFile"]["inode"] = self.value["objects"]["selectedFile"]["inode"]
        with self.assertRaisesRegex(pc.Refusal, "distinct"):
            self.parse()

    def test_claimed_owner_or_filesystem_mismatch(self):
        for field in ("device", "uid", "gid"):
            value = deepcopy(self.value); value["objects"]["siblingFile"][field] += 1
            with self.assertRaisesRegex(pc.Refusal, "same owned"):
                pc.parse_fixture_claim(encoded(value))


class JSONTests(unittest.TestCase):
    def test_size_before_parse_and_bytes_only(self):
        for data in (b"", b" " * 4097, "{}", bytearray(b"{}")):
            with self.assertRaisesRegex(pc.Refusal, "byte budget"):
                pc.parse_fixture_claim(data)

    def test_exact_json_byte_ceiling(self):
        self.assertEqual(pc.decode_claim(b"0" + b" " * 4095, 4096), 0)
        with self.assertRaises(pc.Refusal):
            pc.decode_claim(b"0" + b" " * 4096, 4096)

    def test_duplicate_keys_at_any_depth(self):
        for data in (b'{"a":1,"a":2}', b'{"a":{"b":1,"b":2}}'):
            with self.assertRaises(pc.Refusal):
                pc.decode_claim(data, 4096)

    def test_invalid_utf8_and_nonfinite(self):
        for data in (b'"\xff"', b'NaN', b'Infinity', b'-Infinity', b'1e9999', b'-1e9999', b'1.0', b'{} trailing'):
            with self.assertRaises(pc.Refusal):
                pc.decode_claim(data, 4096)

    def test_recursive_json_refuses(self):
        with self.assertRaises(pc.Refusal):
            pc.decode_claim(b"[" * 1500 + b"0" + b"]" * 1500, 4096)

    def test_nesting_boundary_ignores_quoted_brackets_and_escapes(self):
        pc.decode_claim(b"[" * 16 + b"0" + b"]" * 16, 4096)
        with self.assertRaisesRegex(pc.Refusal, "nesting budget"):
            pc.decode_claim(b"[" * 17 + b"0" + b"]" * 17, 4096)
        value = {"text": "[" * 100 + '\\"' + "]" * 100}
        self.assertEqual(pc.decode_claim(encoded(value), 4096), value)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.rows = [directory(), file(), link()]

    def test_root_and_links_are_separate_immutable_claims(self):
        value = pc.validate_inventory_claim(self.rows)
        self.assertEqual(value.descendants, ("alias", "existing"))
        self.assertEqual(value.resolved_links, (("alias", "existing"),))
        self.assertEqual(value.total_claimed_bytes, 3)
        self.rows[1]["size"] = 99
        self.assertEqual(value.total_claimed_bytes, 3)
        with self.assertRaises(FrozenInstanceError):
            value.descendants = ()

    def test_parser_roundtrip_and_schema(self):
        data = encoded(dict(schemaVersion=1, entries=self.rows))
        self.assertEqual(pc.parse_inventory_claim(data), pc.validate_inventory_claim(self.rows))
        for value in ({"schemaVersion": True, "entries": self.rows}, {"schemaVersion": 1, "entries": self.rows, "trusted": True}):
            with self.assertRaises(pc.Refusal):
                pc.parse_inventory_claim(encoded(value))

    def test_complete_rows_independent_of_order(self):
        self.assertEqual(pc.validate_inventory_claim(self.rows), pc.validate_inventory_claim(list(reversed(self.rows))))

    def test_missing_duplicate_and_non_directory_root(self):
        for rows in (self.rows[1:], self.rows + [directory()], [file(".")]):
            with self.assertRaises(pc.Refusal):
                pc.validate_inventory_claim(rows)

    def test_real_parent_and_no_descendants_under_link(self):
        for rows in ([directory(), file("missing/file")], [directory(), directory("dir"), link("alias", "dir"), file("alias/file")]):
            with self.assertRaisesRegex(pc.Refusal, "real parent"):
                pc.validate_inventory_claim(rows)

    def test_exact_relative_paths(self):
        for path in ("../outside", "/absolute", "a//b", "a/./b", "a/../b", "a/", "a\\b", "a\nb", "a\x7fb", "a\ud800b", "x" * 1025):
            with self.subTest(path=repr(path)), self.assertRaises(pc.Refusal):
                pc.validate_inventory_claim([directory(), file(path)])

    def test_unicode_paths_are_exact_not_normalised(self):
        rows = [directory(), file("é"), file("e\u0301"), link("alias", "é")]
        result = pc.validate_inventory_claim(rows)
        self.assertIn("é", result.descendants); self.assertIn("e\u0301", result.descendants)
        self.assertEqual(dict(result.resolved_links)["alias"], "é")

    def test_entry_budget_before_rows(self):
        for rows in ([], (), [None] * 20001):
            with self.assertRaisesRegex(pc.Refusal, "entry budget"):
                pc.validate_inventory_claim(rows)

    def test_file_and_total_byte_boundaries(self):
        rows = [directory()] + [file(str(i), pc.MAX_FILE_BYTES) for i in range(4)]
        self.assertEqual(pc.validate_inventory_claim(rows).total_claimed_bytes, pc.MAX_TOTAL_BYTES)
        with self.assertRaisesRegex(pc.Refusal, "total byte"):
            pc.validate_inventory_claim(rows + [file("over", 1)])
        with self.assertRaises(pc.Refusal):
            pc.validate_inventory_claim([directory(), file(size=pc.MAX_FILE_BYTES + 1)])

    def test_field_shape_numeric_types_and_kind(self):
        for field, invalid in (("size", True), ("uid", -1), ("gid", 2**32), ("mode", stat.S_IFDIR), ("sha256", "G" * 64), ("kind", [])):
            row = file(); row[field] = invalid
            with self.subTest(field=field), self.assertRaises(pc.Refusal):
                pc.validate_inventory_claim([directory(), row])
        row = file(); row["extra"] = True
        with self.assertRaises(pc.Refusal):
            pc.validate_inventory_claim([directory(), row])

    def test_shared_positive_and_refusal_corpus(self):
        corpus = json.loads((HERE / "inventory-corpus.json").read_bytes())
        self.assertEqual(corpus["schemaVersion"], 1)
        self.assertEqual(len(corpus["cases"]), 19)
        self.assertEqual(len({c["name"] for c in corpus["cases"]}), 19)
        for case in corpus["cases"]:
            with self.subTest(case=case["name"]):
                if case["accepted"]:
                    claim = pc.validate_inventory_claim(case["entries"])
                    self.assertEqual(list(claim.descendants), case["descendants"])
                    self.assertEqual([list(pair) for pair in claim.resolved_links], case["resolvedLinks"])
                else:
                    with self.assertRaises(pc.Refusal) as refusal:
                        pc.validate_inventory_claim(case["entries"])
                    self.assertEqual(str(refusal.exception), case["error"])

    def test_initial_depth_128_and_129_independent_of_producer(self):
        rows = [directory()]
        for depth in range(1, 130):
            path = "/".join(["d"] * depth); rows.append(directory(path))
            if depth == 128:
                self.assertIn(path + "/alias", pc.validate_inventory_claim(rows + [link(path + "/alias", ".")]).descendants)
            elif depth == 129:
                with self.assertRaisesRegex(pc.Refusal, "initial resolution budget"):
                    pc.validate_inventory_claim(rows + [link(path + "/alias", ".")])

    def test_aggregate_budget_shared_across_links(self):
        with patch.object(pc, "MAX_TOTAL_STEPS", 2):
            self.assertEqual(pc.validate_inventory_claim(self.rows).resolved_links, (("alias", "existing"),))
            with self.assertRaisesRegex(pc.Refusal, "aggregate resolution budget"):
                pc.validate_inventory_claim(self.rows + [link("another")])

    def test_step_limit_is_explicit(self):
        with patch.object(pc, "MAX_STEPS", 1):
            with self.assertRaisesRegex(pc.Refusal, "resolution step budget"):
                pc.validate_inventory_claim(self.rows)

    def test_targets_do_not_erase_unsafe_components(self):
        for target in ("/existing", "..", "missing/../existing", "existing/../existing", "alias/../existing", "existing\0", "existing\\", "\ud800"):
            with self.subTest(target=repr(target)), self.assertRaises(pc.Refusal):
                pc.validate_inventory_claim([directory(), file(), link(target=target)])


if __name__ == "__main__":
    unittest.main()
