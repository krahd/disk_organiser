"""Source-only startup deadlines and retained template comparison anchor."""
import hashlib
from pathlib import Path
from types import SimpleNamespace
from contextlib import ExitStack
from unittest.mock import Mock, patch
import unittest

import stage_b_bootstrap as boot
import stage_b_profile as profile
import test_stage_b_driver as dt


class BootstrapBoundaryTests(unittest.TestCase):
    def testExpiredSourceReadRefusesBeforeOpeningAnyDescriptor(self):
        with patch.object(boot.os, 'open') as opened:
            with self.assertRaisesRegex(boot.Refusal, 'expired'):
                boot.read_source('native/fixed.py', 100, check=lambda: (_ for _ in ()).throw(boot.Refusal('expired')))
        opened.assert_not_called()

    def testExpiryInsideSourceReadRetiresEveryDescriptorWithoutAnotherRead(self):
        fixture = dt.SourceReadTests(); fixture.setUp()
        try:
            def check():
                if fixture.read.call_count:
                    raise boot.Refusal('720 deadline')
            with self.assertRaisesRegex(boot.Refusal, '720 deadline'):
                boot.read_source('native/fixed.py', 100, check=check)
            self.assertEqual(fixture.read.call_count, 1)
            self.assertEqual(fixture.close.call_count, fixture.open.call_count)
            self.assertEqual(len(fixture.closed), len(set(fixture.closed)))
        finally:
            fixture.doCleanups()

    def startup(self, *, moved=False, changed=False, expired=False):
        raw, _ = dt.BootstrapTests().profile()
        enabled = raw.replace(b'BUILD_ONLY_ENABLED = False', b'BUILD_ONLY_ENABLED = True')
        workflow = (Path(__file__).parents[1]/'StageB/owned-selected-folder-build.environment-diagnostic.yml.inert').read_bytes()
        environment, _ = dt.BootstrapTests().identity()
        environment.update(boot.STARTUP_FIXED)
        environment.update(ImageOS='macos15', ImageVersion='20260907.0337.1')
        paths = []; clock = [0.0]
        def read(name, limit, **options):
            paths.append(name)
            if 'check' in options:
                options['check']()
            if name == boot.RELATIVE+'/Tools/stage_b_profile.py': return enabled
            if name == profile.WORKFLOW: return workflow + (b'changed' if changed else b'')
            if name == profile.TEMPLATE:
                if moved: raise FileNotFoundError('retained anchor missing')
                return workflow
            raise AssertionError(name)
        def admitted(*args):
            if expired: clock[0] = 720
            return {}, {}
        with ExitStack() as stack:
            stack.enter_context(patch.object(boot.time, 'monotonic', side_effect=lambda: clock[0]))
            stack.enter_context(patch.object(boot, 'read_source', side_effect=read))
            stack.enter_context(patch.object(boot.sys, 'flags', SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1)))
            stack.enter_context(patch.object(boot.sys, 'version_info', (3, 12, 10)))
            stack.enter_context(patch.object(boot.sys, 'executable', profile.PYTHON))
            stack.enter_context(patch.object(boot.sys, 'platform', 'darwin'))
            stack.enter_context(patch.object(boot.os, 'uname', return_value=SimpleNamespace(machine='arm64')))
            stack.enter_context(patch.object(boot.os, 'environ', environment))
            stack.enter_context(patch.object(boot, 'admit_sources', side_effect=admitted))
            stack.enter_context(patch.object(boot, 'system_version', return_value={'fixture': True}))
            load = stack.enter_context(patch.object(boot, 'load_modules'))
            load.return_value.run.return_value = 2  # no operational driver executes
            if moved:
                with self.assertRaisesRegex(FileNotFoundError, 'retained anchor missing'):
                    boot.main(hashlib.sha256(raw).hexdigest())
                load.assert_not_called()
            elif changed or expired:
                with self.assertRaises(boot.Refusal): boot.main(hashlib.sha256(raw).hexdigest())
                load.assert_not_called()
            else:
                self.assertEqual(boot.main(hashlib.sha256(raw).hexdigest()), 2)
                load.assert_called_once(); load.return_value.run.assert_called_once()
                self.assertTrue(callable(load.call_args.kwargs['check']))
        return paths

    def testExactCopiedWorkflowAndRetainedAnchorAdmitSourceOnlyModel(self):
        paths = self.startup()
        self.assertIn(profile.WORKFLOW, paths); self.assertIn(profile.TEMPLATE, paths)

    def testMissingRetainedAnchorRefusesBeforeOperationalImports(self):
        self.startup(moved=True)

    def testChangedActiveWorkflowRefusesBeforeOperationalImports(self):
        self.startup(changed=True)

    def testStartupDeadlineExpiryRefusesBeforeOperationalImports(self):
        self.startup(expired=True)


if __name__ == '__main__': unittest.main()
