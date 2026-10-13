"""Memory-only create-event admission; no workflow or native tool is run."""
from contextlib import ExitStack
import hashlib
import json
import math
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import stage_b_bootstrap as boot
import stage_b_driver as driver
import stage_b_profile as profile
import test_stage_b_driver as dt


BRANCH = 'validation/owned-build-xctest-hooks-once-20261013'
FIELDS = (
    ('github.event_name', 'create'),
    ('github.repository', 'krahd/disk_organiser'),
    ('github.event.ref_type', 'branch'),
    ('github.event.ref', BRANCH),
    ('github.ref', 'refs/heads/' + BRANCH),
)


def condition(raw, expected_number=None):
    """Model this fixed grammar, including GitHub loose numeric equality.

    This is a source oracle for scalar fixture values, not an Actions emulator.
    """
    if expected_number is None: expected_number = profile.EXPECTED_RUN_NUMBER
    start = '  owned-build-only:\n    if: >-\n'
    if raw.count(start) != 1:
        raise AssertionError('one job guard')
    text = raw.split(start)[1].split('    runs-on:', 1)[0]
    expression = ' '.join(line.strip() for line in text.splitlines())
    if not expression.startswith('${{ ') or not expression.endswith(' }}'):
        raise AssertionError('guard expression')
    clauses = expression[4:-3].split(' && ')
    numeric = [('github.run_attempt', 1), ('github.run_number', expected_number)]
    if clauses[-2:] != [key + ' == ' + str(value) for key, value in numeric]:
        raise AssertionError('exact numeric counter/attempt clauses')
    pairs = []
    for clause in clauses[:-2]:
        match = re.fullmatch(r"(github\.[a-z_.]+) == '([A-Za-z0-9_./-]+)'", clause)
        if not match:
            raise AssertionError('literal equality only')
        pairs.append(match.groups())
    if tuple(pairs) != FIELDS:
        raise AssertionError('exact create-job admission')
    def admits(event):
        # GitHub string equality ignores case. This is only an ASCII-fixture
        # source model, not a complete Actions expression implementation.
        for key, expected in pairs:
            value = event.get(key)
            if type(value) is not str:
                return False
            if not value.isascii():
                raise AssertionError('scheduler model is limited to ASCII fixtures')
            if value.lower() != expected.lower():
                return False
        return all(loose_number(event.get(key)) == expected for key, expected in numeric)
    return admits


def loose_number(value):
    # Official Actions coercion: null/false -> 0, true -> 1, empty -> 0;
    # strings use JSON number syntax; arrays/objects or invalid numbers -> NaN.
    if value is None: return 0
    if type(value) is bool: return int(value)
    if type(value) in (int, float): return value
    if type(value) is str:
        if not value.strip(): return 0
        try: parsed = json.loads(value)
        except (ValueError, TypeError): return math.nan
        if type(parsed) in (int, float): return parsed
    return math.nan


def event_fixture():
    return {**dict(FIELDS), 'github.run_attempt': 1,
            'github.run_number': profile.EXPECTED_RUN_NUMBER}


class CreateTransportTests(unittest.TestCase):
    def raw(self):
        return (Path(__file__).parents[1] / 'StageB/owned-selected-folder-build.debug-layout.yml.inert').read_text()

    def testOnlyReservedBranchCreationAdmitsJobPredicate(self):
        admits = condition(self.raw()); event = event_fixture()
        self.assertTrue(admits(event))
        for key, _ in FIELDS:
            for value in ('', 'different', None, 1, event[key] + '/suffix'):
                with self.subTest(key=key, value=value):
                    self.assertFalse(admits({**event, key: value}))
            missing = dict(event); del missing[key]
            self.assertFalse(admits(missing))

    def testSourcePublicationMainMergesTagsAndOldManualEventCannotAdmitJob(self):
        admits = condition(self.raw()); base = event_fixture()
        for name in ('main', 'native/review-create-transport', BRANCH + '-other'):
            self.assertFalse(admits({**base, 'github.event.ref': name, 'github.ref': 'refs/heads/' + name}))
        self.assertFalse(admits({**base, 'github.event.ref_type': 'tag', 'github.ref': 'refs/tags/' + BRANCH}))
        for event in ('push', 'pull_request', 'workflow_dispatch', 'workflow_run', 'repository_dispatch', 'delete'):
            self.assertFalse(admits({**base, 'github.event_name': event}))

    def testCaseVariantSchedulerMatchStillRefusesBeforeOperationalAdmission(self):
        admits = condition(self.raw()); event = event_fixture()
        identity_keys = {
            'github.event_name': 'GITHUB_EVENT_NAME',
            'github.repository': 'GITHUB_REPOSITORY',
            'github.event.ref_type': 'CREATED_REF_TYPE',
            'github.event.ref': 'CREATED_REF',
            'github.ref': 'GITHUB_REF',
        }
        for key, value in FIELDS:
            with self.subTest(key=key):
                self.assertTrue(admits({**event, key: value.swapcase()}))
                self.startup({identity_keys[key]: value.swapcase()})
        variant = 'Validation/owned-build-xctest-hooks-once-20261013'
        self.assertTrue(admits({**event, 'github.event.ref': variant, 'github.ref': 'refs/heads/' + variant}))
        self.startup({'CREATED_REF': variant, 'GITHUB_REF': 'refs/heads/' + variant,
                      'GITHUB_WORKFLOW_REF': profile.REPOSITORY + '/' + profile.WORKFLOW + '@refs/heads/' + variant})
        # Do not imply the local model proves GitHub's Unicode folding semantics.
        with self.assertRaisesRegex(AssertionError, 'ASCII fixtures'):
            admits({**event, 'github.event.ref': 'Välidation/owned-build-xctest-hooks-once-20261013'})

    def testMissingGuardClauseOrDisjunctionCannotSatisfyWorkflowOracle(self):
        raw = self.raw()
        for key, value in FIELDS:
            needle = key + " == '" + value + "'"
            changed = raw.replace(needle, 'true', 1)
            with self.assertRaises(AssertionError): condition(changed)
        with self.assertRaises(AssertionError): condition(raw.replace(' &&', ' ||', 1))

    def testActiveAnchorShapeHasNoSecondTriggerOrExpressionInShell(self):
        raw = self.raw()
        self.assertEqual(re.findall(r'^  ([A-Za-z_-]+):$', raw, re.M), ['create', 'owned-build-only'])
        self.assertIn('EXPECTED_DRIVER_SHA: ${{ github.sha }}', raw)
        self.assertIn('CREATED_REF: ${{ github.event.ref }}', raw)
        self.assertIn('CREATED_REF_TYPE: ${{ github.event.ref_type }}', raw)
        self.assertNotIn('${{', raw.split('        run: |')[1].split('      - name:', 1)[0])
        self.assertEqual(raw.count('uses:'), 2)
        for text in ('contents: read', 'timeout-minutes: 20', 'timeout-minutes: 16',
                     'timeout-minutes: 2', 'persist-credentials: false', 'set-safe-directory: false',
                     'fetch-depth: 1', 'submodules: false', 'lfs: false', 'retention-days: 14'):
            self.assertIn(text, raw)

    def testOriginalManualAnchorRemainsExactHistoricalBytes(self):
        old = (Path(__file__).parents[1] / 'StageB/owned-selected-folder-build.yml.inert').read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(), '75ade725601f8375028f5842060cafdcdbb8e6bc8caae7c40881027e1a13749a')
        self.assertTrue(profile.TEMPLATE.endswith('/owned-selected-folder-build.debug-layout.yml.inert'))
        self.assertEqual(profile.REF, 'refs/heads/' + BRANCH)

    def testNewAnchorBindsEveryHelperAndHostByteWithNormalisedProfile(self):
        tools = Path(__file__).parent
        raw = (tools / 'stage_b_profile.py').read_bytes()
        normalised = raw.replace(b'BUILD_ONLY_ENABLED = True\n', b'BUILD_ONLY_ENABLED = False\n', 1)
        digest = hashlib.sha256(normalised).hexdigest()
        parsed = boot.decode_profile(raw, digest)
        self.assertIn('stage_b_bootstrap.py ' + digest, self.raw())
        self.assertEqual(len(parsed['MODULE_ROWS']), 14)
        self.assertEqual(len(parsed['HOST_ROWS']), 19)
        for name, expected in parsed['MODULE_ROWS']:
            self.assertEqual(hashlib.sha256((tools / name).read_bytes()).hexdigest(), expected, name)
        for name, expected in parsed['HOST_ROWS']:
            self.assertEqual(hashlib.sha256((tools.parent / name).read_bytes()).hexdigest(), expected, name)

    def startup(self, changes):
        raw, digest = dt.BootstrapTests().profile()
        raw = raw.replace(b'BUILD_ONLY_ENABLED = False\n', b'BUILD_ONLY_ENABLED = True\n', 1)
        environment, _ = dt.BootstrapTests().identity()
        environment.update(boot.STARTUP_FIXED)
        environment.update(ImageOS='macos15', ImageVersion='20260907.0337.1')
        environment.update(changes)
        anchor = self.raw().encode()
        def read(name, limit, **kwargs):
            if name == boot.RELATIVE + '/Tools/stage_b_profile.py': return raw
            if name in (profile.WORKFLOW, profile.TEMPLATE): return anchor
            raise AssertionError(name)
        with ExitStack() as stack:
            stack.enter_context(patch.object(boot, 'read_source', side_effect=read))
            stack.enter_context(patch.object(boot.sys, 'flags', SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1)))
            stack.enter_context(patch.object(boot.sys, 'version_info', (3, 12, 10)))
            stack.enter_context(patch.object(boot.sys, 'executable', profile.PYTHON))
            stack.enter_context(patch.object(boot.sys, 'platform', 'darwin'))
            stack.enter_context(patch.object(boot.os, 'uname', return_value=SimpleNamespace(machine='arm64')))
            stack.enter_context(patch.object(boot.os, 'environ', environment))
            admit = stack.enter_context(patch.object(boot, 'admit_sources', return_value=({}, {})))
            stack.enter_context(patch.object(boot, 'system_version', return_value={'fixture': True}))
            load = stack.enter_context(patch.object(boot, 'load_modules'))
            load.return_value.run.return_value = 2
            if changes:
                with self.assertRaises(boot.Refusal): boot.main(digest, '17')
                admit.assert_not_called(); load.assert_not_called()
            else:
                self.assertEqual(boot.main(digest, '17'), 2)
                admit.assert_called_once(); load.assert_called_once()
                self.assertEqual(load.return_value.run.call_args.args[0]['GITHUB_EVENT_NAME'], 'create')

    def testExactCreateEnvelopeReachesOnlyMockedOperationalOwner(self):
        self.startup({})

    def testMalformedOrWrongEventRefusesBeforeOperationalAdmission(self):
        for key, values in (
            ('GITHUB_EVENT_NAME', ('workflow_dispatch', 'push', 'pull_request')),
            ('CREATED_REF_TYPE', ('tag', '', 'branch\0suffix')),
            ('CREATED_REF', ('main', BRANCH + '/suffix', 'x' * 4097)),
            ('GITHUB_REF', ('refs/heads/main', 'refs/tags/' + BRANCH)),
            ('GITHUB_REPOSITORY', ('other/disk_organiser',)),
            ('GITHUB_RUN_ATTEMPT', ('2',)),
            ('CHECKED_OUT_SHA', ('b' * 40,)),
            ('GITHUB_WORKFLOW_SHA', ('b' * 40,)),
            ('GITHUB_WORKFLOW_REF', ('krahd/disk_organiser/' + profile.WORKFLOW + '@refs/heads/main',))):
            for value in values:
                with self.subTest(key=key, value=value): self.startup({key: value})

    def testMissingCreatedFieldsRefuseEvenWithoutStartupWrapper(self):
        environment, parsed = dt.BootstrapTests().identity()
        for key in ('CREATED_REF', 'CREATED_REF_TYPE'):
            missing = dict(environment); del missing[key]
            with self.assertRaises(boot.Refusal): boot.verify_dispatch(missing, b'x', b'x', parsed)

    def testDriverDefenceRejectsWrongCreatedFieldsBeforeAnyOwner(self):
        identity, _ = dt.BootstrapTests().identity()
        for key, value in (('GITHUB_EVENT_NAME', 'workflow_dispatch'), ('CREATED_REF_TYPE', 'tag'),
                           ('CREATED_REF', 'main'), ('GITHUB_REF', 'refs/heads/main'), ('GITHUB_RUN_ATTEMPT', '2')):
            with self.subTest(key=key), patch.object(profile, 'BUILD_ONLY_ENABLED', True), \
                 patch.object(driver.ec, '_source_files') as sources, patch.object(driver.ba, '_issue') as admission, \
                 patch.object(driver.sr.Report, 'create') as report:
                with self.assertRaisesRegex(driver.pc.Refusal, 'driver dispatch identity'):
                    driver.run({**identity, key: value}, {}, started_at=0)
                sources.assert_not_called(); admission.assert_not_called(); report.assert_not_called()

    def testEveryConsumedMarkerRefusesBeforeOperationalAdmission(self):
        for previous in ('validation/owned-build-once-20261012',
                         'validation/owned-build-framework-20261012',
                         'validation/startup-keys-once-20261013',
                         'validation/owned-build-encoding-once-20261013',
                         'validation/owned-build-dir-stream-once-20261013',
                         'validation/owned-build-explicit-self-once-20261013'):
            with self.subTest(previous=previous):
                self.assertNotEqual(previous,BRANCH)
                self.assertFalse(condition(self.raw())({**event_fixture(),
                    'github.event.ref':previous,'github.ref':'refs/heads/'+previous}))
                self.startup({'CREATED_REF':previous,'GITHUB_REF':'refs/heads/'+previous,
                    'GITHUB_WORKFLOW_REF':profile.REPOSITORY+'/'+profile.WORKFLOW+'@refs/heads/'+previous})


if __name__ == '__main__': unittest.main()
