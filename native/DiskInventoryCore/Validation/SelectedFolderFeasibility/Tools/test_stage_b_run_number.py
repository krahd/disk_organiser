"""Counter admission in memory only; never reserve a counter or create an owner."""
import ast
from contextlib import ExitStack
import hashlib
import inspect
import json
from pathlib import Path
import re
import shlex
import unittest
from unittest.mock import patch

import stage_b_bootstrap as boot
import stage_b_profile as profile
import stage_b_workflow_guard as guard
import startup_key_observation as historical
import test_stage_b_create_transport as ct
import test_stage_b_driver as dt
import test_stage_b_interpreter_identity as it

HERE = Path(__file__).parent
ROOT = HERE.parents[4]


class RunNumberTests(unittest.TestCase):
    def profile(self, number=17, enabled=True):
        raw = (HERE/'stage_b_profile.py').read_bytes()
        raw = raw.replace(('EXPECTED_RUN_NUMBER = '+str(profile.EXPECTED_RUN_NUMBER)+'\n').encode(),
                          ('EXPECTED_RUN_NUMBER = '+repr(number)+'\n').encode(), 1)
        raw = raw.replace(b'BUILD_ONLY_ENABLED = True\n', b'BUILD_ONLY_ENABLED = False\n', 1)
        digest = hashlib.sha256(raw).hexdigest()
        if enabled: raw = raw.replace(b'BUILD_ONLY_ENABLED = False\n', b'BUILD_ONLY_ENABLED = True\n', 1)
        return raw, digest

    def main(self, actual='17', *, number=17, enabled=True, environment=None,
             workflow_changed=False, profile_changed=False, admission_fails=False):
        raw, digest = self.profile(number, enabled)
        parsed = boot.decode_profile(raw, digest) if not profile_changed else None
        if profile_changed: raw += b'# changed after hashing\n'
        template = (ROOT/profile.TEMPLATE).read_bytes()
        template = template.replace(('github.run_number == '+str(profile.EXPECTED_RUN_NUMBER)).encode(), ('github.run_number == '+str(number)).encode())
        current = (HERE/'stage_b_profile.py').read_bytes()
        current = current.replace(b'BUILD_ONLY_ENABLED = True\n', b'BUILD_ONLY_ENABLED = False\n', 1)
        template = template.replace(hashlib.sha256(current).hexdigest().encode(), digest.encode())
        values, _ = dt.BootstrapTests().identity()
        values.update(boot.STARTUP_FIXED); values.update(ImageOS='macos15', ImageVersion='20260907.0337.1')
        values.update(environment or {})
        events = []
        def read(name, limit, **options):
            events.append(('read', name))
            if name == boot.RELATIVE+'/Tools/stage_b_profile.py': return raw
            if name == profile.WORKFLOW: return template + (b'changed' if workflow_changed else b'')
            if name == profile.TEMPLATE: return template
            raise AssertionError(name)
        real_dispatch = boot.verify_dispatch
        def dispatch(*args):
            events.append('dispatch'); return real_dispatch(*args)
        real_counter = boot.verify_run_number
        def counter(*args):
            events.append('counter'); return real_counter(*args)
        def sources(*args):
            events.append('sources')
            if admission_fails: raise boot.Refusal('source closure')
            return {}, {}
        with ExitStack() as stack:
            stack.enter_context(it.runtime())
            stack.enter_context(patch.object(boot.os, 'environ', values))
            reads = stack.enter_context(patch.object(boot, 'read_source', side_effect=read))
            stack.enter_context(patch.object(boot, 'verify_dispatch', side_effect=dispatch))
            stack.enter_context(patch.object(boot, 'verify_run_number', side_effect=counter))
            admit = stack.enter_context(patch.object(boot, 'admit_sources', side_effect=sources))
            stack.enter_context(patch.object(boot, 'system_version', return_value={'fixture': True}))
            load = stack.enter_context(patch.object(boot, 'load_modules'))
            load.return_value.run.return_value = 2
            failure = None; result = None
            try: result = boot.main(digest, actual)
            except boot.Refusal as error: failure = error
            return result, failure, load, admit, reads, events, parsed

    def testStrictAsciiPositiveNumberBoundaries(self):
        for value in ('1', '17', '999999999', '1000000000'):
            self.assertEqual(boot.parse_run_number(value), int(value))
        for value in ('0', '1000000001', '9999999999', '1'*11):
            with self.assertRaises(boot.Refusal): boot.parse_run_number(value)

    def testMalformedTypesAndSpellingsRefuse(self):
        for value in (None, True, False, 17, 17.0, b'17', [], {}, '', '017', '+17', '-17',
                      ' 17', '17 ', '17\n', '1.7e1', '17.0', '0x11', 'NaN', 'Infinity',
                      '１７', '١٧', '17\0', '17; echo bad', '$(echo 17)', '1'*4097):
            with self.subTest(value=repr(value)), self.assertRaises(boot.Refusal):
                boot.parse_run_number(value)

    def testUnconfiguredSentinelNeverAdmitsAnyActualValue(self):
        for value in ('0', '1', '17', '1000000000', None):
            with self.assertRaisesRegex(boot.Refusal, 'unconfigured'):
                boot.verify_run_number(value, {'EXPECTED_RUN_NUMBER': 0})

    def testExpectedValueIsExactIntegerNeverBooleanOrString(self):
        for value in (None, True, False, '17', 17.0, -1, 0, 1000000001):
            with self.assertRaises(boot.Refusal):
                boot.verify_run_number('17', {'EXPECTED_RUN_NUMBER': value})

    def testProfileAllowsZeroOnlyWithDisabledBoolean(self):
        raw, digest = self.profile(0, False)
        self.assertEqual(boot.decode_profile(raw, digest)['EXPECTED_RUN_NUMBER'], 0)
        raw, digest = self.profile(0, True)
        with self.assertRaisesRegex(boot.Refusal, 'profile run number'): boot.decode_profile(raw, digest)

    def testProfilePositiveBoundariesInBothBooleanStates(self):
        for number in (1, 17, 1000000000):
            for enabled in (False, True):
                raw, digest = self.profile(number, enabled)
                parsed = boot.decode_profile(raw, digest)
                self.assertEqual(parsed['EXPECTED_RUN_NUMBER'], number)
                self.assertIs(parsed['BUILD_ONLY_ENABLED'], enabled)

    def testProfileRejectsMissingDuplicateMalformedOrOversizedCounter(self):
        for value in (None, True, False, '17', 17.0, -1, 1000000001):
            raw, digest = self.profile(value, False)
            with self.assertRaisesRegex(boot.Refusal, 'profile run number'): boot.decode_profile(raw, digest)
        raw, _ = self.profile(17, False)
        for changed in (raw.replace(b'EXPECTED_RUN_NUMBER = 17\n', b''), raw+b'EXPECTED_RUN_NUMBER = 17\n'):
            with self.assertRaises(boot.Refusal): boot.decode_profile(changed, hashlib.sha256(changed).hexdigest())

    def testCounterIsHashBoundAndOnlyBooleanIsNormalised(self):
        raw, digest = self.profile(17, False)
        changed = raw.replace(b'EXPECTED_RUN_NUMBER = 17\n', b'EXPECTED_RUN_NUMBER = 18\n')
        with self.assertRaisesRegex(boot.Refusal, 'hash mismatch'): boot.decode_profile(changed, digest)
        self.assertTrue(boot.decode_profile(raw.replace(b'= False\n', b'= True\n', 1), digest)['BUILD_ONLY_ENABLED'])

    def testOnlySelectedCounterPassesEitherDuplicateArrivalOrder(self):
        for order in (('17', '18'), ('18', '17'), ('17', '16'), ('16', '17')):
            admitted = []
            for counter in order:
                _, error, load, admit, _, _, _ = self.main(counter)
                if error is None:
                    admitted.append(counter); load.return_value.run.assert_called_once()
                else:
                    load.assert_not_called(); admit.assert_not_called()
            self.assertEqual(admitted, ['17'])

    def testLaterDifferentCounterNeverBecomesFallbackAfterFailure(self):
        _, error, load, _, _, _, _ = self.main('17', admission_fails=True)
        self.assertIsNotNone(error); load.assert_not_called()
        for actual in ('18', '19', '16'):
            _, error, load, admit, _, _, _ = self.main(actual)
            self.assertIsNotNone(error); load.assert_not_called(); admit.assert_not_called()

    def testRerunAttemptTwoRefusesEvenForMatchingCounter(self):
        for attempt in ('2', '01', '1.0', ' 1', '', True, 1):
            _, error, load, admit, _, _, _ = self.main(environment={'GITHUB_RUN_ATTEMPT': attempt})
            self.assertIsNotNone(error); load.assert_not_called(); admit.assert_not_called()

    def testCorrectCounterStillRequiresEveryDispatchIdentity(self):
        identity, _ = dt.BootstrapTests().identity()
        for name in identity:
            _, error, load, admit, _, events, _ = self.main(environment={name: 'different'})
            self.assertIsNotNone(error, name); load.assert_not_called(); admit.assert_not_called()
            self.assertNotIn('counter', events)

    def testConsumedRefsStillRefuseWithMatchingCounter(self):
        for ref in ('owned-build-once-20261012', 'owned-build-framework-20261012', 'startup-keys-once-20261013'):
            ref = 'refs/heads/validation/'+ref
            _, error, load, admit, _, _, _ = self.main(environment={
                'GITHUB_REF': ref, 'CREATED_REF': ref.removeprefix('refs/heads/'),
                'GITHUB_WORKFLOW_REF': profile.REPOSITORY+'/'+profile.WORKFLOW+'@'+ref})
            self.assertIsNotNone(error); load.assert_not_called(); admit.assert_not_called()

    def testChangedWorkflowAndChangedProfileRefuseBeforeCounterAndOwners(self):
        for options in ({'workflow_changed': True}, {'profile_changed': True}):
            _, error, load, admit, _, events, _ = self.main(**options)
            self.assertIsNotNone(error); load.assert_not_called(); admit.assert_not_called()
            self.assertNotIn('counter', events)

    def testCounterRefusalPrecedesSourceImportsAndOwnerCreation(self):
        for actual in ('18', '', '017', '1000000001', None):
            _, error, load, admit, _, events, _ = self.main(actual)
            self.assertIsNotNone(error); load.assert_not_called(); admit.assert_not_called()
            self.assertEqual(events[-2:], ['dispatch', 'counter'])

    def testSourceClosureStillPrecedesOperationalImportsWithCorrectCounter(self):
        _, error, load, admit, _, events, _ = self.main(admission_fails=True)
        self.assertRegex(str(error), 'source closure'); admit.assert_called_once(); load.assert_not_called()
        self.assertEqual(events[-3:], ['dispatch', 'counter', 'sources'])

    def testSuccessfulMockIncludesOnlyBoundedIntegerInIdentity(self):
        result, error, load, admit, _, events, _ = self.main()
        self.assertIsNone(error); self.assertEqual(result, 2); admit.assert_called_once()
        identity = load.return_value.run.call_args.args[0]
        self.assertIs(type(identity['run_number']), int); self.assertEqual(identity['run_number'], 17)
        self.assertLessEqual(len(json.dumps(identity).encode()), 65536)
        self.assertEqual(events[-3:], ['dispatch', 'counter', 'sources'])

    def testCliRequiresExactlyHashAndCounterArguments(self):
        tree = ast.parse((HERE/'stage_b_bootstrap.py').read_bytes())
        entry = next(n for n in tree.body if isinstance(n, ast.If) and ast.unparse(n.test)=="__name__ == '__main__'")
        self.assertIn('len(sys.argv) != 3', ast.unparse(entry))
        calls = [n for n in ast.walk(entry) if isinstance(n, ast.Call) and ast.unparse(n.func)=='main']
        self.assertEqual([ast.unparse(n) for n in calls], ['main(sys.argv[1], sys.argv[2])'])
        self.assertEqual(list(inspect.signature(boot.main).parameters), ['expected_profile_hash', 'actual_run_number'])
        self.assertTrue(all(p.default is inspect.Parameter.empty for p in inspect.signature(boot.main).parameters.values()))

    def testCounterTransportIsQuotedAndNotInEighteenKeyStartupMap(self):
        raw = (ROOT/profile.TEMPLATE).read_text()
        self.assertEqual(raw.count('ACTUAL_RUN_NUMBER: ${{ github.run_number }}'), 1)
        shell = raw.split('        run: |\n', 1)[1].split('      - name:', 1)[0]
        self.assertEqual(shell.count('"$ACTUAL_RUN_NUMBER"'), 1)
        self.assertNotIn('${{', shell)
        terminal = shell.split('terminal="$(', 1)[1].split(')"', 1)[0].replace('\\\n', ' ')
        words = shlex.split(terminal)
        python = words.index(profile.PYTHON)
        self.assertEqual({s.split('=', 1)[0] for s in words[2:python]}, boot.STARTUP_KEYS)
        self.assertEqual(len(boot.STARTUP_KEYS), 18)
        self.assertEqual(words[-1], '$ACTUAL_RUN_NUMBER')
        self.assertNotIn('ACTUAL_RUN_NUMBER', boot.STARTUP_KEYS)
        self.assertNotIn('GITHUB_RUN_NUMBER', boot.STARTUP_KEYS)

    def testSchedulerLooseNumericCoercionIsDistinctFromStrictBootstrap(self):
        raw = (ROOT/profile.TEMPLATE).read_text().replace('github.run_number == '+str(profile.EXPECTED_RUN_NUMBER), 'github.run_number == 17')
        accepts = ct.condition(raw, 17)
        event = {**dict(ct.FIELDS), 'github.run_attempt': 1}
        for value in (17, 17.0, '17', '17.0', '1.7e1', ' 17 '):
            self.assertTrue(accepts({**event, 'github.run_number': value}), repr(value))
            if value != '17':
                with self.assertRaises(boot.Refusal): boot.parse_run_number(value)
        for value in (None, False, True, '', '017', '0x11', 'wrong', [], {}, 'NaN', 'Infinity', 18):
            self.assertFalse(accepts({**event, 'github.run_number': value}), repr(value))
        self.assertTrue(accepts({**event, 'github.run_number':17, 'github.run_attempt':True}))
        _, error, load, _, _, _, _ = self.main(environment={'GITHUB_RUN_ATTEMPT':True})
        self.assertIsNotNone(error); load.assert_not_called()

    def testSchedulerNullEmptyAndBooleanCoercionFixtures(self):
        raw = (ROOT/profile.TEMPLATE).read_text().replace(
            'github.run_number == '+str(profile.EXPECTED_RUN_NUMBER), 'github.run_number == 0')
        accepts = ct.condition(raw, 0)
        event = {**dict(ct.FIELDS), 'github.run_attempt':1}
        for value in (None, False, '', ' ', 0, '0', '-0'):
            self.assertTrue(accepts({**event, 'github.run_number':value}))
        # GitHub actual run numbers begin at one. Sentinel zero is deliberately
        # not a prediction, reservation or a runnable source configuration.
        for value in (1, 17, 1000000000):
            self.assertFalse(accepts({**event, 'github.run_number':value}))

    def testNumericConditionLiteralAndProfileMustAgree(self):
        raw = (ROOT/profile.TEMPLATE).read_text()
        self.assertTrue(callable(ct.condition(raw, profile.EXPECTED_RUN_NUMBER)))
        for changed in (raw.replace('github.run_number == '+str(profile.EXPECTED_RUN_NUMBER), 'github.run_number == 1'),
                        raw.replace('github.run_number == '+str(profile.EXPECTED_RUN_NUMBER), "github.run_number == '"+str(profile.EXPECTED_RUN_NUMBER)+"'"),
                        raw.replace('github.run_attempt == 1', 'github.run_attempt == 2'),
                        raw.replace('github.run_attempt == 1 &&', ''),
                        raw.replace('github.run_number == '+str(profile.EXPECTED_RUN_NUMBER), 'github.run_number >= 0')):
            with self.assertRaises(AssertionError): ct.condition(changed, profile.EXPECTED_RUN_NUMBER)

    def testFrozenSourceRemainsDisabledAndUnconfiguredWithBothWorkflowsAbsent(self):
        # Retain the original disabled-zero refusal, and explicitly distinguish
        # the later reviewed positive literal's two repository Boolean states.
        self.assertIs(type(profile.BUILD_ONLY_ENABLED), bool)
        self.assertIs(type(profile.EXPECTED_RUN_NUMBER), int)
        self.assertEqual(profile.EXPECTED_RUN_NUMBER, 7)
        if profile.BUILD_ONLY_ENABLED:
            self.assertEqual((ROOT/profile.WORKFLOW).read_bytes(), (ROOT/profile.TEMPLATE).read_bytes())
        else:
            self.assertFalse((ROOT/profile.WORKFLOW).exists())
        self.assertFalse((ROOT/historical.WORKFLOW).exists())
        self.assertTrue(guard.check(ROOT, profile.BUILD_ONLY_ENABLED))
        raw, digest = self.profile(0, False)
        with patch.object(boot, 'read_source', return_value=raw), it.runtime(), patch.object(boot,'load_modules') as load:
            with self.assertRaisesRegex(boot.Refusal, 'disabled'): boot.main(digest, '17')
        load.assert_not_called()

    def testNewAnchorHasOnlyHashCounterClauseAndQuotedTransportDelta(self):
        prior = (HERE.parent/'StageB/owned-selected-folder-build.encoding-attempt.yml.inert').read_text()
        raw = (HERE/'stage_b_profile.py').read_bytes()
        normal = raw.replace(b'BUILD_ONLY_ENABLED = True\n', b'BUILD_ONLY_ENABLED = False\n', 1)
        digest = hashlib.sha256(normal).hexdigest()
        expected = prior.replace('5ec43dbf0be0bdadba84219393bbd367540d04d229d950584c63e34dee8c4f0f', digest)
        expected = expected.replace("github.ref == '"+profile.REF+"' }}",
            "github.ref == '"+profile.REF+"' &&\n          github.run_attempt == 1 &&\n          github.run_number == "+str(profile.EXPECTED_RUN_NUMBER)+" }}")
        expected = expected.replace('          EXPECTED_DRIVER_SHA: ${{ github.sha }}',
            '          EXPECTED_DRIVER_SHA: ${{ github.sha }}\n          ACTUAL_RUN_NUMBER: ${{ github.run_number }}')
        expected = expected.replace('stage_b_bootstrap.py '+digest+')"',
            'stage_b_bootstrap.py '+digest+' "$ACTUAL_RUN_NUMBER")"')
        self.assertEqual((ROOT/profile.TEMPLATE).read_text(), expected)

    def testSevenHistoricalAnchorsAndConsumedDiagnosticKeepExactBytes(self):
        raw = (HERE/'startup_key_observation.py').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), '7e3f577e43b58053b26a1665176b7da7675e559695bcb160a67fb08976e4887d')
        # Full prior-anchor hash inventory is also retained in the freeze receipt.
        predecessor = (HERE.parent/'StageB/owned-selected-folder-build.encoding-attempt.yml.inert').read_bytes()
        self.assertEqual(hashlib.sha256(predecessor).hexdigest(), '443941896ee98159062a767719ffb020ba257ec966d732eefd8c8f08fb4f65c9')
        old = (HERE.parent/'StageB/startup-key-observation.profile.inert').read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(), historical.PROFILE_HASH)
        self.assertIs(historical.decode_profile(old, historical.PROFILE_HASH)['BUILD_ONLY_ENABLED'], False)
        with self.assertRaises(historical.Refusal): historical.decode_profile((HERE/'stage_b_profile.py').read_bytes(), historical.PROFILE_HASH)

    def testRunSevenCopyChangesOnlyCounterAndNormalisedProfilePin(self):
        prior = (HERE.parent/'StageB/owned-selected-folder-build.run-number.yml.inert').read_bytes()
        self.assertEqual(hashlib.sha256(prior).hexdigest(), '23597f48cad17482be7900241e1611438b0e89a9c96bf38ac7addfbcc56486cb')
        raw = (HERE/'stage_b_profile.py').read_bytes()
        normal = raw.replace(b'BUILD_ONLY_ENABLED = True\n', b'BUILD_ONLY_ENABLED = False\n', 1)
        expected = prior.replace(b'17ac4693ee3d23517f9744244b4bb7dc6fbee7322c51495d65be008464c849c1',hashlib.sha256(normal).hexdigest().encode())
        expected = expected.replace(b'github.run_number == 0', b'github.run_number == 7')
        self.assertEqual((ROOT/profile.TEMPLATE).read_bytes(), expected)
        self.assertEqual(profile.REF, 'refs/heads/validation/owned-build-encoding-once-20261013')

    def testFrozenSevenIsOnlyAdmittedCounterAndRerunStillRefuses(self):
        for counter in ('1','2','3','4','5','6','7','8','9','1000000000'):
            result, error, load, admit, _, _, _ = self.main(counter, number=7)
            if counter == '7':
                self.assertIsNone(error); self.assertEqual(result,2)
                self.assertEqual(load.return_value.run.call_args.args[0]['run_number'],7)
            else:
                self.assertIsNotNone(error); load.assert_not_called(); admit.assert_not_called()
        _, error, load, admit, _, _, _ = self.main('7', number=7, environment={'GITHUB_RUN_ATTEMPT':'2'})
        self.assertIsNotNone(error); load.assert_not_called(); admit.assert_not_called()


if __name__ == '__main__': unittest.main()
