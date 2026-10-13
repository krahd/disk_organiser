"""Exact source-byte regressions; no XCTest compilation, launch or syscall."""
import ast
import hashlib
import json
from pathlib import Path
import re
import unittest

import stage_b_profile as profile

HERE = Path(__file__).parents[1]
OLD_UI_SHA = '68efd59235788b79855358437a0e7c0ffdd63f7e7169a40fb10dceacfafd420f'
OLD_PROFILE_SHA = 'd8936fc85ed3e1f2eeb44a48de5989218f263f452b1f10acafe471d73b98d49f'
REPLACEMENTS = (
    (b'    override func setUpWithError() throws {', b'    @MainActor\n    override func setUp() async throws {'),
    (b'    override func tearDownWithError() throws {', b'    @MainActor\n    override func tearDown() async throws {'),
)


def signature_only(raw):
    if type(raw) is not bytes:
        return False
    for before, after in REPLACEMENTS:
        if raw.count(after) != 1:
            return False
        raw = raw.replace(after, before, 1)
    return hashlib.sha256(raw).hexdigest() == OLD_UI_SHA


class XCTestHookSourceTests(unittest.TestCase):
    def testOnlyAsyncMainActorHookSignaturesChange(self):
        raw = (HERE/'UITests/SelectionProbeUITests.swift').read_bytes()
        self.assertTrue(signature_only(raw))
        self.assertEqual(len(re.findall(rb'func test\w+\(', raw)), 3)
        self.assertEqual(raw.count(b'@MainActor'), 3)
        for forbidden in (b'assumeIsolated', b'@unchecked', b'nonisolated', b'DispatchQueue',
                          b'Task {', b'await super.', b'override func setUpWithError',
                          b'override func tearDownWithError'):
            self.assertNotIn(forbidden, raw)

    def testWrongHooksIsolationAndBodyChangesRefuse(self):
        raw = (HERE/'UITests/SelectionProbeUITests.swift').read_bytes()
        variants = [raw.replace(after, before, 1) for before, after in REPLACEMENTS]
        variants += [raw.replace(b'    @MainActor\n', b'', 1),
                     raw.replace(b' async throws {', b' throws {', 1),
                     raw.replace(b'app?.terminate()', b'// no retirement', 1),
                     raw.replace(b'continueAfterFailure = false', b'continueAfterFailure = true', 1),
                     raw.replace(b'try FixtureProof.verify(fixture)', b'// proof omitted', 1),
                     raw.replace(b'timeout: 10', b'timeout: 20', 1),
                     raw.replace(b'        app.launch()', b'        app.launch()\n        app.launch()', 1),
                     raw + b'// extra\n', None, raw.decode()]
        for changed in variants:
            with self.subTest(kind=type(changed).__name__):
                self.assertNotEqual(changed, raw)
                self.assertFalse(signature_only(changed))

    def testInactiveRowsAndHashOnlyAnchorPreserveConsumedNine(self):
        # Preserve the exact inactive hook checkpoint as historical source.
        raw = (HERE/'StageB/xctest-hooks.profile.inert').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         'aad1352d03542cd8dbe75aa551427c59681cfa0670768f515f821c40bbe8f06b')
        previous = (HERE/'StageB/run-nine.profile.inert').read_bytes()
        self.assertEqual(hashlib.sha256(previous).hexdigest(), OLD_PROFILE_SHA)
        old = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(previous).body
               if isinstance(n, ast.Assign)}
        current = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(raw).body
                   if isinstance(n, ast.Assign)}
        self.assertEqual(set(current), set(old))
        for key in current:
            if key not in ('HOST_SOURCE_COMMIT', 'HOST_ROWS_SHA256', 'HOST_ROWS', 'TEMPLATE'):
                self.assertEqual(current[key], old[key], key)
        self.assertEqual(profile.HOST_SOURCE_COMMIT, '9eed307659fead2eb5e2824e0d6964277d48c6e6')
        rows = tuple((name, hashlib.sha256((HERE/name).read_bytes()).hexdigest())
                     for name, _ in profile.HOST_ROWS)
        self.assertEqual(len(rows), 19)
        self.assertEqual(rows, profile.HOST_ROWS)
        self.assertEqual([name for (name, h), (_, prior) in zip(rows, old['HOST_ROWS']) if h != prior],
                         ['UITests/SelectionProbeUITests.swift'])
        self.assertEqual(hashlib.sha256(json.dumps(list(rows), sort_keys=True,
                         separators=(',', ':')).encode()).hexdigest(), profile.HOST_ROWS_SHA256)
        previous_anchor = (HERE/'StageB/owned-selected-folder-build.run-nine.yml.inert').read_bytes()
        self.assertEqual(hashlib.sha256(previous_anchor).hexdigest(),
                         'a9f0f0cf01fa9f5d66cbc5c9884855620af9eda6528d40c930e7a822db00abac')
        normal = raw.replace(b'BUILD_ONLY_ENABLED = True\n', b'BUILD_ONLY_ENABLED = False\n', 1)
        actual = (HERE/'StageB/owned-selected-folder-build.xctest-hooks.yml.inert').read_bytes()
        self.assertEqual(previous_anchor.count(OLD_PROFILE_SHA.encode()), 1)
        self.assertEqual(actual, previous_anchor.replace(OLD_PROFILE_SHA.encode(),
                         hashlib.sha256(normal).hexdigest().encode()))
        self.assertEqual(current['EXPECTED_RUN_NUMBER'], 9)
        self.assertEqual(current['REF'], 'refs/heads/validation/owned-build-explicit-self-once-20261013')
        repo = HERE.parents[3]
        self.assertIs(current['BUILD_ONLY_ENABLED'], False)
        self.assertIs(type(profile.BUILD_ONLY_ENABLED), bool)
        if profile.BUILD_ONLY_ENABLED:
            self.assertEqual((repo/profile.WORKFLOW).read_bytes(), (repo/profile.TEMPLATE).read_bytes())
        else:
            self.assertFalse((repo/profile.WORKFLOW).exists())
        self.assertFalse((repo/'.github/workflows/owned-startup-key-observation.yml').exists())


if __name__ == '__main__':
    unittest.main()
