"""Source-byte regression only; no compiler, native host or filesystem observation."""
import hashlib
import json
from pathlib import Path
import unittest

import stage_b_profile as profile

HERE = Path(__file__).parents[1]
OLD_CONTROLLER_SHA = '891bc69043799b537c9cee8aefbf68f76c88bf0d028a9de6750c54f250194351'
POSITIONS = ((60, 33, 'generation'), (60, 54, 'phase'), (63, 21, 'preDenial'), (64, 24, 'closeRequested'), (64, 41, 'closeNow'), (65, 21, 'show'), (66, 37, 'chooseFolder'), (67, 43, 'fail'), (90, 33, 'generation'), (94, 24, 'stopping'), (96, 21, 'afterRetirement'), (98, 62, 'fixture'), (99, 54, 'fail'), (101, 17, 'scope'), (102, 17, 'show'), (114, 48, 'generation'), (114, 69, 'work'), (115, 23, 'phase'), (116, 17, 'show'), (123, 33, 'generation'), (123, 54, 'work'), (124, 17, 'scope'), (124, 30, 'work'), (127, 21, 'activeDenials'), (127, 47, 'afterRetirement'), (127, 117, 'stopping'), (129, 21, 'activeDenials'), (129, 47, 'afterRetirement'), (130, 41, 'fail'), (162, 33, 'generation'), (162, 54, 'phase'), (165, 27, 'writeReceipt'), (166, 25, 'show'), (167, 28, 'closeRequested'), (167, 45, 'closeNow'), (170, 21, 'show'), (171, 24, 'closeRequested'), (171, 41, 'closeNow'), (172, 43, 'fail'))


def qualification_only(raw):
    if type(raw) is not bytes:
        return False
    try:
        lines = raw.decode('utf-8').splitlines(keepends=True)
        for line, column, token in sorted(POSITIONS):
            at = column - 1
            if lines[line-1][at:at+5+len(token)] != 'self.'+token:
                return False
            lines[line-1] = lines[line-1][:at]+lines[line-1][at+5:]
        return hashlib.sha256(''.join(lines).encode()).hexdigest() == OLD_CONTROLLER_SHA
    except (UnicodeError, IndexError):
        return False


class ExplicitSelfSourceTests(unittest.TestCase):
    def testExactlyThirtyNineQualificationsRetainEveryOtherControllerByte(self):
        raw = (HERE/'Host/ProbeController.swift').read_bytes()
        self.assertTrue(qualification_only(raw))
        self.assertEqual(len(POSITIONS), 39)
        self.assertEqual(len(set(POSITIONS)), 39)
        self.assertEqual(raw.count(b'[weak self'), 10)
        self.assertEqual(raw.count(b'guard let self'), 5)
        self.assertEqual(raw.count(b'Task { @MainActor'), 5)
        self.assertIn(b'selected.retire()\n                guard let self, self.generation == token, self.work === operation', raw)

    def testMissingQualificationsAndOwnershipMutationsRefuse(self):
        raw = (HERE/'Host/ProbeController.swift').read_bytes()
        lines = raw.decode().splitlines(keepends=True)
        for line, column, token in POSITIONS:
            prior = sum(1 for n, c, _ in POSITIONS if n == line and c < column)
            at = column - 1 + prior * 5
            changed = lines.copy()
            self.assertEqual(changed[line-1][at:at+5+len(token)], 'self.'+token)
            changed[line-1] = changed[line-1][:at]+changed[line-1][at+5:]
            with self.subTest(line=line, column=column):
                self.assertFalse(qualification_only(''.join(changed).encode()))
        mutations = (raw.replace(b'[weak self', b'[self', 1),
                     raw.replace(b'selected.retire()', b'// omitted retirement', 1),
                     raw.replace(b'self.generation == token', b'self.generation != token', 1),
                     raw.replace(b'self.work === operation', b'self.work !== operation', 1),
                     raw.replace(b'Task { @MainActor', b'Task {', 1),
                     raw + b'// unrelated change\n', b'', b'\xff', None, raw.decode())
        for changed in mutations:
            with self.subTest(kind=type(changed).__name__):
                self.assertFalse(qualification_only(changed))

    def testInactiveAnchorBindsCorrectedRowsAndConsumedEight(self):
        self.assertIs(profile.BUILD_ONLY_ENABLED, False)
        self.assertEqual(profile.EXPECTED_RUN_NUMBER, 8)
        self.assertEqual(profile.REF, 'refs/heads/validation/owned-build-dir-stream-once-20261013')
        self.assertEqual(profile.HOST_SOURCE_COMMIT, 'b567f3468ae6f5383e5e857b58448c5042ca2836')
        rows = tuple((name, hashlib.sha256((HERE/name).read_bytes()).hexdigest())
                     for name, _ in profile.HOST_ROWS)
        self.assertEqual(len(rows), 19)
        self.assertEqual(rows, profile.HOST_ROWS)
        self.assertEqual(hashlib.sha256(json.dumps(list(rows), sort_keys=True,
                         separators=(',', ':')).encode()).hexdigest(), profile.HOST_ROWS_SHA256)
        prior = (HERE/'StageB/owned-selected-folder-build.run-eight.yml.inert').read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(),
                         'f8c3344760f6748f6db5d25b25d925fa0c59bd8d992a5a253b23b4a9ae33dc2f')
        raw = (HERE/'Tools/stage_b_profile.py').read_bytes()
        self.assertEqual(profile.TEMPLATE,
                         'native/DiskInventoryCore/Validation/SelectedFolderFeasibility/StageB/owned-selected-folder-build.explicit-self.yml.inert')
        actual = (HERE/'StageB/owned-selected-folder-build.explicit-self.yml.inert').read_bytes()
        self.assertEqual(actual, prior.replace(
            b'f5620beb83272cc6c0beec27634d4732120bf45420035b98eec340cb3f27f998',
            hashlib.sha256(raw).hexdigest().encode()))
        repo = HERE.parents[3]
        self.assertFalse((repo/profile.WORKFLOW).exists())
        self.assertFalse((repo/'.github/workflows/owned-startup-key-observation.yml').exists())


if __name__ == '__main__':
    unittest.main()
