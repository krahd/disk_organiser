"""Source-byte regressions only; no Xcode, signing, binary read or launch."""
from pathlib import Path
import hashlib
import ast
import json
import stage_b_profile as profile
import re
import unittest

HERE = Path(__file__).parents[1]
PATH = 'Probe.xcodeproj/project.pbxproj'
BASE_SHA = 'f2fd8dd1cb16af05622c8e0f9d850fbeff72cf52544b27f4c15ac5529af91d63'
ADDITION = b'ENABLE_DEBUG_DYLIB = NO; '
TARGET = b'\t\t32AAE8F4C4612E570A4A6829 = { isa = XCBuildConfiguration;'


def debug_target_only(raw):
    if type(raw) is not bytes or raw.count(ADDITION) != 1:
        return False
    rows = [row for row in raw.splitlines() if row.startswith(TARGET)]
    if len(rows) != 1 or ADDITION not in rows[0]:
        return False
    if b'PRODUCT_NAME = OwnedFolderProbe;' not in rows[0] or b'name = Debug;' not in rows[0]:
        return False
    return hashlib.sha256(raw.replace(ADDITION, b'', 1)).hexdigest() == BASE_SHA


class DebugLayoutSourceTests(unittest.TestCase):
    def testOnlyHostDebugLayoutSettingChanges(self):
        after = (HERE/PATH).read_bytes()
        before = after.replace(ADDITION, b'', 1)
        self.assertEqual(hashlib.sha256(before).hexdigest(), BASE_SHA)
        self.assertTrue(debug_target_only(after))
        self.assertEqual(after.replace(ADDITION, b'', 1), before)
        self.assertEqual(len(after)-len(before), len(ADDITION))
        for key in (b'SWIFT_OPTIMIZATION_LEVEL', b'CODE_SIGN', b'ENABLE_APP_SANDBOX',
                    b'ENABLE_HARDENED_RUNTIME', b'DEVELOPMENT_TEAM', b'SWIFT_VERSION'):
            self.assertEqual(re.findall(key+rb'[^;]*;', before), re.findall(key+rb'[^;]*;', after))

    def testWrongScopeSettingsAndOtherByteChangesRefuse(self):
        raw = (HERE/PATH).read_bytes()
        without = raw.replace(ADDITION, b'', 1)
        variants = [without, raw.replace(ADDITION, b'ENABLE_DEBUG_DYLIB = YES; ', 1),
                    raw.replace(ADDITION, ADDITION*2, 1),
                    raw.replace(b'SWIFT_OPTIMIZATION_LEVEL = "-Onone";', b'SWIFT_OPTIMIZATION_LEVEL = "-O";', 1),
                    raw.replace(b'CODE_SIGNING_ALLOWED = NO;', b'CODE_SIGNING_ALLOWED = YES;', 1),
                    raw.replace(b'ENABLE_APP_SANDBOX = NO;', b'ENABLE_APP_SANDBOX = YES;', 1),
                    raw.replace(b'ENABLE_HARDENED_RUNTIME = NO;', b'ENABLE_HARDENED_RUNTIME = YES;', 1),
                    raw + b'// unrelated\n', None, raw.decode()]
        # Project Debug, host Release, and UI-test Debug are all wrong scopes.
        for target in (b'184B519F8E1416CCE38CFFD7', b'6A096A88B6386BC712CA491E', b'EFD8814F42B842756271FEF2'):
            lines = without.splitlines(keepends=True)
            for i, line in enumerate(lines):
                if line.startswith(b'\t\t'+target+b' ='):
                    lines[i] = line.replace(b'buildSettings = { ', b'buildSettings = { '+ADDITION, 1)
            variants.append(b''.join(lines))
        for changed in variants:
            with self.subTest(kind=type(changed).__name__):
                self.assertNotEqual(changed, raw)
                self.assertFalse(debug_target_only(changed))


    def testInactiveLayoutPinsRetainConsumedTenAndExactCommands(self):
        historical = (HERE/'StageB/run-ten.profile.inert').read_bytes()
        self.assertEqual(hashlib.sha256(historical).hexdigest(), 'd477601dc29b780da3bc3fb6fd4a1c366fac61196c88407263aa1fc66d89e9fb')
        previous = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(historical).body
                    if isinstance(n, ast.Assign)}
        raw = (HERE/'Tools/stage_b_profile.py').read_bytes()
        current = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(raw).body
                   if isinstance(n, ast.Assign)}
        self.assertEqual(set(current), set(previous))
        for key in current:
            if key not in ('HOST_SOURCE_COMMIT', 'HOST_ROWS_SHA256', 'HOST_ROWS', 'TEMPLATE', 'BUILD_ONLY_ENABLED'):
                self.assertEqual(current[key], previous[key], key)
        self.assertEqual(current['HOST_SOURCE_COMMIT'], '33c3e70daa2a3f89896e8d2141e01aff577592bb')
        rows = tuple((name, hashlib.sha256((HERE/name).read_bytes()).hexdigest())
                     for name, _ in current['HOST_ROWS'])
        self.assertEqual(len(rows), 19)
        self.assertEqual(rows, current['HOST_ROWS'])
        self.assertEqual([name for (name, digest), (_, old) in zip(rows, previous['HOST_ROWS']) if digest != old],
                         ['Probe.xcodeproj/project.pbxproj'])
        self.assertEqual(hashlib.sha256(json.dumps(list(rows), sort_keys=True,
                         separators=(',', ':')).encode()).hexdigest(), current['HOST_ROWS_SHA256'])
        prior = (HERE/'StageB/owned-selected-folder-build.run-ten.yml.inert').read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(), '6da698f7606c79f48413e578b8b3bd84f1d6df54a732fa2e34d9015778d12218')
        normal = raw.replace(b'BUILD_ONLY_ENABLED = True\n', b'BUILD_ONLY_ENABLED = False\n', 1)
        actual = (HERE/'StageB/owned-selected-folder-build.debug-layout.yml.inert').read_bytes()
        self.assertEqual(actual, prior.replace(b'd477601dc29b780da3bc3fb6fd4a1c366fac61196c88407263aa1fc66d89e9fb', hashlib.sha256(normal).hexdigest().encode()))
        self.assertEqual(current['EXPECTED_RUN_NUMBER'], 10)
        self.assertEqual(current['REF'], 'refs/heads/validation/owned-build-xctest-hooks-once-20261013')
        repo = HERE.parents[3]
        self.assertIs(type(current['BUILD_ONLY_ENABLED']), bool)
        if current['BUILD_ONLY_ENABLED']:
            self.assertEqual((repo/current['WORKFLOW']).read_bytes(), (repo/current['TEMPLATE']).read_bytes())
        else:
            self.assertFalse((repo/current['WORKFLOW']).exists())
        self.assertFalse((repo/'.github/workflows/owned-startup-key-observation.yml').exists())
        import stage_b_commands
        self.assertEqual(stage_b_commands.COMMAND_COUNT, 31)


if __name__ == '__main__':
    unittest.main()
