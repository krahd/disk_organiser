"""Memory-only launcher identity facts; no launcher, workflow or native run."""
from contextlib import ExitStack, contextmanager
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import stage_b_bootstrap as boot
import stage_b_profile as profile
import stage_b_workflow_guard as workflow_guard
import test_stage_b_driver as dt


PYTHON = '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12'
EXPECTED = {'schema': 1, 'executable': PYTHON, 'version': [3, 12, 10],
            'implementation': 'cpython',
            'flags': {'isolated': 1, 'no_site': 1, 'dont_write_bytecode': 1},
            'platform': 'darwin', 'machine': 'arm64'}


@contextmanager
def runtime(**changes):
    values = dict(executable=PYTHON, version_info=(3, 12, 10, 'final', 0),
                  implementation=SimpleNamespace(name='cpython'), platform='darwin',
                  flags=SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1))
    machine = changes.pop('machine', 'arm64'); values.update(changes)
    with ExitStack() as stack:
        for key, value in values.items():
            stack.enter_context(patch.object(boot.sys, key, value))
        stack.enter_context(patch.object(boot.os, 'uname', return_value=SimpleNamespace(machine=machine)))
        yield


class InterpreterIdentityTests(unittest.TestCase):
    def testExactFixedFactsHaveSevenKeysAndBoundedJSONShape(self):
        with runtime():
            facts = boot.interpreter_identity(vars(profile))
        self.assertEqual(facts, EXPECTED)
        self.assertEqual(set(facts), {'schema', 'executable', 'version', 'implementation', 'flags', 'platform', 'machine'})
        raw = json.dumps(facts, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        self.assertLessEqual(len(raw), 512)
        self.assertEqual(json.loads(raw), EXPECTED)
        self.assertTrue(all(type(v) is int for v in facts['version']))
        self.assertTrue(all(type(v) is int for v in facts['flags'].values()))

    def testCachedUnversionedDifferentAndMalformedExecutableRefuse(self):
        for value in ('/Users/runner/hostedtoolcache/Python/3.12.10/arm64/bin/python3',
                      '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3',
                      '/usr/bin/python3', PYTHON + '.other', '', None, 1, b'bytes',
                      'x' * 257, '\u00e9' * 256, PYTHON + '\0'):
            with self.subTest(value=value), runtime(executable=value), self.assertRaises(boot.Refusal):
                boot.interpreter_identity(vars(profile))

    def testProfileCannotSubstituteAnotherMatchingExecutable(self):
        other = '/usr/bin/python3'
        with runtime(executable=other), self.assertRaisesRegex(boot.Refusal, 'fixed framework interpreter'):
            boot.interpreter_identity({**vars(profile), 'PYTHON': other})

    def testVersionMustBeExactlyThreeBoundedIntegerComponents(self):
        for value in ((3, 12, 9), (3, 12, 11), (3, 13, 10), (3, 12),
                      (3, 12, 10.0), (3, 12, True), (3, 12, 65536), ('3', 12, 10),
                      None, '3.12.10', [3, 12, 10], (3, 12, 10, 0, 0, 0)):
            with self.subTest(value=value), runtime(version_info=value), self.assertRaises(boot.Refusal):
                boot.interpreter_identity(vars(profile))

    def testImplementationMustBeExactBoundedCPython(self):
        for value in ('pypy', 'CPython', '', None, 1, b'cpython', 'x' * 17, '\u00e9', 'cpython\0'):
            with self.subTest(value=value), runtime(implementation=SimpleNamespace(name=value)), self.assertRaises(boot.Refusal):
                boot.interpreter_identity(vars(profile))

    def testEachFlagMustBeIntegerOne(self):
        for key in EXPECTED['flags']:
            for value in (0, 2, True, 1.0, '1', None):
                flags = {**EXPECTED['flags'], key: value}
                with self.subTest(key=key, value=value), runtime(flags=SimpleNamespace(**flags)), self.assertRaises(boot.Refusal):
                    boot.interpreter_identity(vars(profile))

    def testPlatformAndArchitectureRetainExactAdmissionAndBounds(self):
        for key, values in (('platform', ('linux', 'Darwin', '', None, 'x' * 17)),
                            ('machine', ('x86_64', 'ARM64', '', None, 'x' * 17))):
            for value in values:
                with self.subTest(key=key, value=value), runtime(**{key: value}), self.assertRaises(boot.Refusal):
                    boot.interpreter_identity(vars(profile))

    def startup(self, changes, *, succeeds=False):
        raw, digest = dt.BootstrapTests().profile()
        enabled = raw.replace(b'BUILD_ONLY_ENABLED = False\n', b'BUILD_ONLY_ENABLED = True\n', 1)
        environment, _ = dt.BootstrapTests().identity()
        environment.update(boot.STARTUP_FIXED)
        environment.update(ImageOS='macos15', ImageVersion='20260907.0337.1')
        template = (Path(__file__).parents[1] / 'StageB/owned-selected-folder-build.explicit-self.yml.inert').read_bytes()
        def read(name, limit, **kwargs):
            if name == boot.RELATIVE + '/Tools/stage_b_profile.py': return enabled
            if name in (profile.WORKFLOW, profile.TEMPLATE): return template
            raise AssertionError(name)
        with runtime(**changes), patch.object(boot, 'read_source', side_effect=read) as reads, \
             patch.object(boot.os, 'environ', environment), \
             patch.object(boot, 'verify_dispatch', wraps=boot.verify_dispatch) as dispatch, \
             patch.object(boot, 'admit_sources', return_value=({}, {})) as admitted, \
             patch.object(boot, 'system_version', return_value={'fixture': True}), \
             patch.object(boot, 'load_modules') as load:
            load.return_value.run.return_value = 2
            if succeeds:
                self.assertEqual(boot.main(digest, '17'), 2)
                identity = load.return_value.run.call_args.args[0]
                self.assertEqual(identity['interpreter'], EXPECTED)
                self.assertLessEqual(len(json.dumps(identity).encode()), 65536)
                self.assertEqual(reads.call_count, 3); dispatch.assert_called_once(); admitted.assert_called_once()
                load.assert_called_once(); load.return_value.run.assert_called_once()
            else:
                with self.assertRaises(boot.Refusal): boot.main(digest, '17')
                # Only the fixed profile can be read before rejection. No
                # workflow/source admission, operational import or owner exists.
                self.assertEqual(reads.call_count, 1)
                dispatch.assert_not_called(); admitted.assert_not_called(); load.assert_not_called()

    def testExactRuntimeFactsReachOnlyMockedDriverInIdentityEnvelope(self):
        self.startup({}, succeeds=True)

    def testEveryIdentityMismatchRefusesBeforeDispatchSourcesOrOwners(self):
        for changes in ({'executable': '/usr/bin/python3'}, {'version_info': (3, 12, 11)},
                        {'implementation': SimpleNamespace(name='pypy')}, {'platform': 'linux'},
                        {'machine': 'x86_64'}, {'executable': None}, {'executable': 'x' * 257},
                        {'flags': SimpleNamespace(isolated=2, no_site=1, dont_write_bytecode=1)}):
            with self.subTest(changes=changes): self.startup(changes)

    def testObservedFactsAreFreshValuesWithoutArbitraryRuntimeFields(self):
        with runtime():
            first = boot.interpreter_identity(vars(profile)); second = boot.interpreter_identity(vars(profile))
        first['flags']['isolated'] = 0; first['version'][0] = 0
        self.assertEqual(second, EXPECTED)
        self.assertNotIn('environ', second); self.assertNotIn('path', second)

    def testBothHistoricalAnchorsRemainExactAndSuccessorIsInactive(self):
        folder = Path(__file__).parents[1] / 'StageB'
        expected = {
            'owned-selected-folder-build.yml.inert': '75ade725601f8375028f5842060cafdcdbb8e6bc8caae7c40881027e1a13749a',
            'owned-selected-folder-build.create.yml.inert': '87f1bfbea213a008890e6c3fee04c7bd2ae9590e59d2f37f2ace9b174c2e02d6',
            'owned-selected-folder-build.framework.yml.inert': '84f4225638c054a43f2fffb82062abb4ca8da49c287ada7e43e5307fa68fcffc'}
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest)
        # Retain the historical method identity while checking the exact
        # currently reviewed state. Both states have independent paired oracles.
        self.assertIs(type(profile.BUILD_ONLY_ENABLED), bool)
        self.assertTrue(profile.TEMPLATE.endswith('/owned-selected-folder-build.explicit-self.yml.inert'))
        self.assertEqual(profile.PYTHON, PYTHON)
        self.assertEqual(profile.REF, 'refs/heads/validation/owned-build-dir-stream-once-20261013')
        repo = Path(__file__).parents[5]
        active = repo / profile.WORKFLOW
        if profile.BUILD_ONLY_ENABLED:
            self.assertEqual(active.read_bytes(), (repo / profile.TEMPLATE).read_bytes())
        else:
            self.assertFalse(active.exists())

    def testWorkflowPresenceOracleRetainsBothDisabledAndExactEnabledStates(self):
        repo = Path(__file__).parents[5]
        template = (repo / profile.TEMPLATE).read_bytes()
        # Pure byte-map models: no workflow is executed or activation written.
        self.assertTrue(workflow_guard.validate({}, {}, template, False))
        self.assertTrue(workflow_guard.validate({profile.WORKFLOW: template}, {}, template, True))
        for enabled, files in ((False, {profile.WORKFLOW: template}), (True, {}),
                               (True, {profile.WORKFLOW: template + b'changed'})):
            with self.subTest(enabled=enabled, files=list(files)), self.assertRaises(AssertionError):
                workflow_guard.validate(files, {}, template, enabled)
        for enabled in (None, 0, 1, 'True'):
            with self.subTest(enabled=enabled), self.assertRaises(AssertionError):
                workflow_guard.validate({}, {}, template, enabled)


if __name__ == '__main__': unittest.main()
