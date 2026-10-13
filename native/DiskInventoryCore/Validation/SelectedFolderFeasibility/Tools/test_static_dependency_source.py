"""Source/hash oracles for the inactive static-only successor; no binary access."""
from pathlib import Path
import ast
import hashlib
import unittest

import stage_b_commands as commands
import stage_b_profile as profile
from test_stage_b_commands import COMMANDS, CEILINGS

HERE=Path(__file__).parents[1]
ROOT=HERE.parents[3]
sha=lambda b:hashlib.sha256(b).hexdigest()

def values(raw):
    return {n.targets[0].id:ast.literal_eval(n.value) for n in ast.parse(raw).body if isinstance(n,ast.Assign)}


class StaticDependencySourceTests(unittest.TestCase):
    def testHistoricalProfileAndOnlyFourNewModulePins(self):
        old=(HERE/'StageB/debug-layout.profile.inert').read_bytes()
        self.assertEqual(sha(old),'f4857f38dbb1e3182c76dc94302e4d8e2d78b26b6c8259b213c4d78351de3e86')
        prior=values(old)
        # Preserve exact inactive inspector composition as historical evidence.
        raw=(HERE/'StageB/static-dependencies.profile.inert').read_bytes()
        self.assertEqual(sha(raw),'23d7f29b67f48c99fae6fbdd67d24dc775fe1a2163c72131a10e66e492c7f37b')
        current=values(raw)
        self.assertEqual(set(current),set(prior))
        for key in current:
            if key not in ('MODULE_ROWS','TEMPLATE','BUILD_ONLY_ENABLED'):
                self.assertEqual(current[key],prior[key],key)
        self.assertEqual([n for (n,h),(_,o) in zip(current['MODULE_ROWS'],prior['MODULE_ROWS']) if h!=o],
                         ['bounded_process.py','native_observations.py','stage_b_commands.py','experiment_controller.py'])
        self.assertEqual([n for n,_ in current['MODULE_ROWS']],[n for n,_ in prior['MODULE_ROWS']])
        for name,digest in current['MODULE_ROWS']:
            self.assertEqual(sha((HERE/'Tools'/name).read_bytes()),digest)
        for name,digest in current['HOST_ROWS']:
            self.assertEqual(sha((HERE/name).read_bytes()),digest)
        template=(ROOT/current['TEMPLATE']).read_bytes()
        previous=(ROOT/prior['TEMPLATE']).read_bytes()
        normal=raw.replace(b'BUILD_ONLY_ENABLED = True\n',b'BUILD_ONLY_ENABLED = False\n',1)
        self.assertEqual(template,previous.replace(sha(old).encode(),sha(normal).encode()))
        self.assertEqual(current['EXPECTED_RUN_NUMBER'],10)
        self.assertIs(current['BUILD_ONLY_ENABLED'],False)
        live=values((HERE/'Tools/stage_b_profile.py').read_bytes())
        self.assertEqual(live['MODULE_ROWS'],current['MODULE_ROWS'])
        self.assertEqual(live['HOST_ROWS'],current['HOST_ROWS'])
        self.assertEqual(live['HOST_SOURCE_COMMIT'],current['HOST_SOURCE_COMMIT'])
        current=live;template=(ROOT/current['TEMPLATE']).read_bytes()
        self.assertIs(type(current['BUILD_ONLY_ENABLED']),bool)
        if current['BUILD_ONLY_ENABLED']:
            self.assertEqual((ROOT/current['WORKFLOW']).read_bytes(),template)
        else:self.assertFalse((ROOT/current['WORKFLOW']).exists())
        self.assertFalse((ROOT/'.github/workflows/owned-startup-key-observation.yml').exists())

    def testOriginalThirtyOneCommandBodiesAndLimitsRemainExact(self):
        raw=(HERE/'Tools/stage_b_commands.py').read_bytes()
        start=raw.index(b'    inspector = ');end=raw.index(b'    return versions',start)
        before=raw[:start]+raw[end:]
        before=before.replace(b'COMMAND_COUNT = 32\n',b'COMMAND_COUNT = 31\n',1)
        before=before.replace(b'signing + (inspector,) +',b'signing +',1)
        self.assertEqual(sha(before),'1bb5b495c97e72cacf4d31ce4c77c6c7503e2a5d2ff26f921accc05c17b3e81b')
        self.assertEqual(commands._commands('/private/tmp/disk-selection-build-memory',
                         '/private/tmp/disk-selection-build-memory/Products'),tuple(zip(COMMANDS,CEILINGS)))
        self.assertEqual(len(COMMANDS),32);self.assertEqual(COMMANDS[7][1:4],('-arch','all','-L'))
        self.assertEqual((commands.WORK_SECONDS,commands.TOTAL_SECONDS,commands.RETIREMENT_SECONDS),(720,900,9))
        self.assertEqual(CEILINGS[7],20)

    def testToolAllowlistAddsOnlyFixedClassicLeaf(self):
        raw=(HERE/'Tools/bounded_process.py').read_bytes()
        addition=b',\n         "/Applications/Xcode_16.4.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/otool-classic"'
        self.assertEqual(raw.count(addition),1)
        self.assertEqual(sha(raw.replace(addition,b'',1)),
                         '677e0a1a1bd05d88f40e070374c27f49dab1babccef3a24af4ba4e87ea1e84b6')


if __name__=='__main__':unittest.main()
