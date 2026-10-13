"""Read source only; these assertions do not compile or call a Darwin syscall."""
import hashlib
import json
from pathlib import Path
import unittest

import stage_b_profile as profile

HERE = Path(__file__).parents[1]
OLD_HOST_SHA = 'd948b0bbb6421211321b7c7afe4af4f2eb734505d168fe8989dfb9bc978d69c8'
OLD_PROFILE_SHA = 'bae1acb235a50b83c25cd4b98a277290a8e0788aac405967f29788f6cdb5dfe1'
OLD_DECLARATION = b'    private var streams: [OpaquePointer] = []\n'
NEW_DECLARATION = b'    private var streams: [UnsafeMutablePointer<DIR>] = []\n'


def declaration_only(raw):
    return (type(raw) is bytes and raw.count(NEW_DECLARATION) == 1 and
            OLD_DECLARATION not in raw and
            hashlib.sha256(raw.replace(NEW_DECLARATION, OLD_DECLARATION)).hexdigest() == OLD_HOST_SHA)


class DirectoryStreamSourceTests(unittest.TestCase):
    def testTypedStoragePreservesEveryOtherDescriptorOwnershipByte(self):
        raw = (HERE/'Host/ProbeDescriptors.swift').read_bytes()
        self.assertTrue(declaration_only(raw))
        for changed in (raw.replace(NEW_DECLARATION, OLD_DECLARATION),
                        raw.replace(NEW_DECLARATION, b'    private var streams: [UnsafeMutableRawPointer] = []\n'),
                        raw.replace(b'closedir(stream)', b'closedir(UnsafeMutablePointer<DIR>(stream))'),
                        raw.replace(b'owned.remove(at: index)', b'owned.removeAll()'),
                        raw.replace(b'streams.append(stream)', b'// dropped stream'),
                        raw + b'// unrelated change\n', None, raw.decode()):
            with self.subTest(changed=type(changed).__name__):
                self.assertFalse(declaration_only(changed))

    def testCorrectedHostRowsBindTheReviewedHostOnlyObject(self):
        self.assertEqual(profile.HOST_SOURCE_COMMIT, '93db00f686daf5acac064beadf3115cad7a36605')
        self.assertEqual(len(profile.HOST_ROWS), 19)
        rows = tuple((name, hashlib.sha256((HERE/name).read_bytes()).hexdigest())
                     for name, _ in profile.HOST_ROWS)
        self.assertEqual(rows, profile.HOST_ROWS)
        self.assertEqual(hashlib.sha256(json.dumps(list(rows), sort_keys=True,
                         separators=(',', ':')).encode()).hexdigest(), profile.HOST_ROWS_SHA256)
        self.assertEqual(dict(rows)['Host/ProbeDescriptors.swift'],
                         'bedff3611948962f46173df27a0e3b4a361d4e8cdd6902cbdc241dac1704a4cf')

    def testNewInactiveAnchorChangesOnlyTheCurrentProfileHash(self):
        prior = (HERE/'StageB/owned-selected-folder-build.run-seven.yml.inert').read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(),
                         '30ba204fc1a3a11e17b6abed7483b3f2b1ff992661449af01b486bc9c46a774e')
        raw = (HERE/'Tools/stage_b_profile.py').read_bytes()
        self.assertIn(b'BUILD_ONLY_ENABLED = False\n', raw)
        self.assertIs(profile.BUILD_ONLY_ENABLED, False)
        self.assertEqual(profile.EXPECTED_RUN_NUMBER, 7)
        self.assertEqual(profile.TEMPLATE,
                         'native/DiskInventoryCore/Validation/SelectedFolderFeasibility/StageB/owned-selected-folder-build.dir-stream.yml.inert')
        actual = (HERE/'StageB/owned-selected-folder-build.dir-stream.yml.inert').read_bytes()
        self.assertEqual(actual, prior.replace(OLD_PROFILE_SHA.encode(), hashlib.sha256(raw).hexdigest().encode()))
        repo = HERE.parents[3]
        self.assertFalse((repo/profile.WORKFLOW).exists())
        self.assertFalse((repo/'.github/workflows/owned-startup-key-observation.yml').exists())


if __name__ == '__main__':
    unittest.main()
