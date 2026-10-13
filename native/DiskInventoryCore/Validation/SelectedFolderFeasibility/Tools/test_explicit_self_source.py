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
        # Reconstruct the exact inactive checkpoint; its old pin stays historical.
        historical = (HERE/'StageB/run-nine.profile.inert').read_bytes()
        self.assertEqual(hashlib.sha256(historical).hexdigest(), 'd8936fc85ed3e1f2eeb44a48de5989218f263f452b1f10acafe471d73b98d49f')
        historical = historical.replace(b'BUILD_ONLY_ENABLED = True\n', b'BUILD_ONLY_ENABLED = False\n', 1)
        historical = historical.replace(b'EXPECTED_RUN_NUMBER = 9\n', b'EXPECTED_RUN_NUMBER = 8\n', 1)
        historical = historical.replace(b'validation/owned-build-explicit-self-once-20261013', b'validation/owned-build-dir-stream-once-20261013')
        historical = historical.replace(b'owned-selected-folder-build.run-nine.yml.inert', b'owned-selected-folder-build.explicit-self.yml.inert')
        historical = historical.replace(b'Reviewed explicit-self host pins for immutable nine; final execution gate remains.', b'Inactive explicit-self host pins; consumed eight remains disabled.')
        self.assertEqual(hashlib.sha256(historical).hexdigest(),
                         'cab0811251d93ba65f19a34453f35df04bff9a2b93fd26772bacb2722c61817c')
        self.assertEqual(profile.HOST_SOURCE_COMMIT, '9eed307659fead2eb5e2824e0d6964277d48c6e6')
        rows = tuple((name, hashlib.sha256((HERE/name).read_bytes()).hexdigest())
                     for name, _ in profile.HOST_ROWS)
        self.assertEqual(len(rows), 19)
        self.assertEqual(rows, profile.HOST_ROWS)
        self.assertEqual(hashlib.sha256(json.dumps(list(rows), sort_keys=True,
                         separators=(',', ':')).encode()).hexdigest(), profile.HOST_ROWS_SHA256)
        prior = (HERE/'StageB/owned-selected-folder-build.run-eight.yml.inert').read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(),
                         'f8c3344760f6748f6db5d25b25d925fa0c59bd8d992a5a253b23b4a9ae33dc2f')
        actual = (HERE/'StageB/owned-selected-folder-build.explicit-self.yml.inert').read_bytes()
        self.assertEqual(actual, prior.replace(
            b'f5620beb83272cc6c0beec27634d4732120bf45420035b98eec340cb3f27f998',
            hashlib.sha256(historical).hexdigest().encode()))
        repo = HERE.parents[3]
        self.assertEqual(hashlib.sha256(actual).hexdigest(),
                         'aae9b778a4077d0382245d32fdd51f3f00e0b2201e7ee75eed46f504fea09634')
        self.assertFalse((repo/'.github/workflows/owned-startup-key-observation.yml').exists())


if __name__ == '__main__':
    unittest.main()
