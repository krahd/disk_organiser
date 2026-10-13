"""Memory-only optional-name admission; no native or filesystem owner executes."""
import ast
from collections.abc import Mapping
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import bounded_process as bp
import experiment_controller as ec
import stage_b_bootstrap as boot
import stage_b_profile as profile
import startup_key_observation as observation
import test_stage_b_driver as dt
import test_stage_b_interpreter_identity as it

MARKER = '__CF_USER_TEXT_ENCODING'
HERE = Path(__file__).parent


class ObservedMapping(Mapping):
    """Forbids bulk/optional reads and mutation; records the actual accesses."""
    def __init__(self, data, *, forbid_all=False):
        self.data = dict(data); self.reads = []; self.iterations = 0; self.forbid_all = forbid_all
    def __iter__(self):
        self.iterations += 1
        return iter(self.data)
    def __len__(self): return len(self.data)
    def __getitem__(self, name):
        if self.forbid_all or name == MARKER: raise AssertionError('forbidden value access')
        self.reads.append(name)
        return self.data[name]
    def items(self): raise AssertionError('bulk access')
    def values(self): raise AssertionError('bulk access')
    def __setitem__(self, *args): raise AssertionError('mutation')
    def __delitem__(self, *args): raise AssertionError('mutation')
    def clear(self): raise AssertionError('mutation')
    def pop(self, *args): raise AssertionError('mutation')
    def update(self, *args): raise AssertionError('mutation')


class EncodingMarkerTests(unittest.TestCase):
    def environment(self):
        return {**dict.fromkeys(boot.STARTUP_IDENTITY, 'identity'), **boot.STARTUP_FIXED}

    def testExactEighteenAndOptionalNineteenCopyOnlyRequiredValues(self):
        for optional in (False, True):
            env = ObservedMapping({**self.environment(), **({MARKER: object()} if optional else {})})
            before = dict(env.data)
            result = boot.startup_environment(env)
            self.assertEqual(result, self.environment()); self.assertEqual(len(result), 18)
            self.assertIs(type(result), dict); self.assertEqual(env.iterations, 1)
            self.assertEqual(set(env.reads), boot.STARTUP_KEYS); self.assertEqual(len(env.reads), 18)
            self.assertEqual(env.data, before); self.assertNotIn(MARKER, result)
            env.data['GITHUB_RUN_ID'] = 'later'
            self.assertEqual(result['GITHUB_RUN_ID'], 'identity')

    def testOptionalValueIsNeverInspectedForAnyTypeOrSize(self):
        for value in (None, object(), '', 'PRIVATE'*10000, b'private', {'PRIVATE': 'value'}, True, 1):
            env = ObservedMapping({**self.environment(), MARKER: value})
            self.assertEqual(boot.startup_environment(env), self.environment())
            self.assertIs(env.data[MARKER], value)
            self.assertNotIn(MARKER, env.reads)

    def testEveryMissingRequiredKeyRefusesBeforeValuesWithOrWithoutMarker(self):
        for optional in (False, True):
            for missing in sorted(boot.STARTUP_KEYS):
                data = self.environment(); del data[missing]
                if optional: data[MARKER] = object()
                env = ObservedMapping(data, forbid_all=True)
                with self.assertRaises(boot.StartupEnvironmentRefusal) as caught:
                    boot.startup_environment(env)
                d = caught.exception.key_diagnostic
                self.assertEqual(d['missing_expected'], [missing]); self.assertEqual(env.reads, [])
                self.assertEqual(d['known_system_presence'][MARKER], optional)
                self.assertEqual(d['unexpected_count'], int(optional)); self.assertEqual(d['unknown_count'], 0)

    def testEveryOtherExtraNameRefusesBeforeValuesAndRetainsFixedPresence(self):
        rejected = ('PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT','PYTHONWARNINGS',
                    'PYTHONBREAKPOINT','PYTHONSAFEPATH','BASH_ENV','ENV','LD_PRELOAD',
                    'DYLD_INSERT_LIBRARIES','DYLD_LIBRARY_PATH','HTTP_PROXY','HTTPS_PROXY',
                    'ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy',
                    'GITHUB_TOKEN','ACTIONS_RUNTIME_TOKEN','ACTIONS_ID_TOKEN_REQUEST_TOKEN',
                    'SSH_AUTH_SOCK','AWS_SECRET_ACCESS_KEY','HOME','TMPDIR','GITHUB_OUTPUT',
                    'LC_CTYPE','__PYVENV_LAUNCHER__','_',MARKER.lower(),MARKER+' ',
                    'PRIVATE\nNAME','é-private',b'private',123)
        for optional in (False, True):
            for extra in rejected:
                data = {**self.environment(), extra: object()}
                if optional: data[MARKER] = object()
                env = ObservedMapping(data, forbid_all=True)
                with self.assertRaises(boot.StartupEnvironmentRefusal) as caught:
                    boot.startup_environment(env)
                d = caught.exception.key_diagnostic
                self.assertEqual(d['known_system_presence'][MARKER], optional)
                self.assertEqual(d['unexpected_count'], 1 + int(optional))
                self.assertEqual(env.reads, [])
                self.assertNotIn('PRIVATE', json.dumps(boot.startup_refusal_record(caught.exception)))

    def testOptionalPresenceDoesNotRelaxRequiredValueOrFixedSettingGuards(self):
        for key in sorted(boot.STARTUP_KEYS):
            for value in ('', 'x'*4097, 'a\0b', 1, True, b'bytes', None):
                env = ObservedMapping({**self.environment(), MARKER: object(), key: value})
                with self.assertRaisesRegex(boot.Refusal, 'startup environment values'):
                    boot.startup_environment(env)
        for key in boot.STARTUP_FIXED:
            env = ObservedMapping({**self.environment(), MARKER: object(), key: 'changed'})
            with self.assertRaisesRegex(boot.Refusal, 'fixed startup environment'):
                boot.startup_environment(env)

    def main_context(self, changes=None, *, optional=True):
        stack = ExitStack(); self.addCleanup(stack.close)
        raw, _ = dt.BootstrapTests().profile()
        raw = raw.replace(b'BUILD_ONLY_ENABLED = True\n', b'BUILD_ONLY_ENABLED = False\n', 1)
        enabled = raw.replace(b'BUILD_ONLY_ENABLED = False\n', b'BUILD_ONLY_ENABLED = True\n', 1)
        values, _ = dt.BootstrapTests().identity()
        values.update(boot.STARTUP_FIXED); values.update(ImageOS='macos15', ImageVersion='20260907.0337.1')
        if optional: values[MARKER] = object()
        env = ObservedMapping(values)
        template = (HERE.parents[4]/profile.TEMPLATE).read_bytes()
        def read(name, limit, **options):
            if name == boot.RELATIVE+'/Tools/stage_b_profile.py': return enabled
            if name in (profile.WORKFLOW, profile.TEMPLATE): return template
            raise AssertionError(name)
        stack.enter_context(it.runtime(**(changes or {})))
        stack.enter_context(patch.object(boot.os, 'environ', env))
        reads = stack.enter_context(patch.object(boot, 'read_source', side_effect=read))
        dispatch = stack.enter_context(patch.object(boot, 'verify_dispatch', wraps=boot.verify_dispatch))
        admit = stack.enter_context(patch.object(boot, 'admit_sources', return_value=({}, {})))
        stack.enter_context(patch.object(boot, 'system_version', return_value={'fixture': True}))
        load = stack.enter_context(patch.object(boot, 'load_modules')); load.return_value.run.return_value = 2
        return env, reads, dispatch, admit, load, hashlib.sha256(raw).hexdigest()

    def testEveryRuntimeMismatchRefusesBeforeOptionalMappingObservation(self):
        changes = [dict(executable='/usr/bin/python3'), dict(version_info=(3,12,11)),
                   dict(implementation=SimpleNamespace(name='pypy')), dict(platform='linux'),
                   dict(machine='x86_64')]
        for name in ('isolated','no_site','dont_write_bytecode'):
            for value in (0, 2, True, 1.0, '1'):
                changes.append(dict(flags=SimpleNamespace(**{**it.EXPECTED['flags'],name:value})))
        for change in changes:
            with self.subTest(change=change):
                env, reads, dispatch, admit, load, digest = self.main_context(change)
                with self.assertRaises(boot.Refusal): boot.main(digest, '17')
                self.assertEqual(env.iterations,0); self.assertEqual(env.reads,[])
                initial_flag_refusal = 'flags' in change and any(
                    not getattr(change['flags'], name) for name in it.EXPECTED['flags'])
                self.assertEqual(reads.call_count,0 if initial_flag_refusal else 1)
                dispatch.assert_not_called(); admit.assert_not_called(); load.assert_not_called()
                self.doCleanups()

    def testMockedMainKeepsOptionalValueOutOfDispatchAndIdentityReport(self):
        env, reads, dispatch, admit, load, digest = self.main_context()
        before = dict(env.data)
        self.assertEqual(boot.main(digest, '17'),2)
        self.assertEqual(env.data,before); self.assertEqual(env.iterations,1)
        self.assertEqual(len(dispatch.call_args.args[0]),18)
        self.assertNotIn(MARKER,dispatch.call_args.args[0]); self.assertNotIn(MARKER,env.reads)
        identity = load.return_value.run.call_args.args[0]
        self.assertNotIn(MARKER,json.dumps(identity)); self.assertNotIn('environment',identity)
        self.assertEqual(identity['interpreter'],it.EXPECTED)
        self.assertEqual(reads.call_count,3); admit.assert_called_once(); load.assert_called_once()

    def experiment(self):
        workspace = SimpleNamespace(path='/private/tmp/disk-selection-build-memory', products_path='/private/tmp/disk-selection-build-memory/Products')
        return ec.Experiment(ec._CONTROLLER_KEY, workspace, SimpleNamespace(claim=b'fixture'), 'a'*40, (), (), ())

    def testChildEnvironmentAndContextContainOnlySixExplicitValues(self):
        with patch.object(ec.os,'environ',ObservedMapping({MARKER:object()},forbid_all=True)):
            experiment = self.experiment()
            expected = {'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','DEVELOPER_DIR':ec.no.DEVELOPER,
                        'HOME':experiment.workspace.path+'/Home','TMPDIR':experiment.workspace.path+'/Temp',
                        'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8'}
            self.assertEqual(experiment.environment,expected)
            signature = SimpleNamespace(identifier='owned',executable='owned',cdhash='a'*40,entitlements={})
            with patch.object(ec.pc,'decode_claim',return_value={'runID':'owned','caseID':'owned'}):
                context = json.loads(experiment._context(SimpleNamespace(signatures=[signature],toolchain={}), 'owned.xctestrun'))
            self.assertEqual(context['environment'],expected);self.assertNotIn(MARKER,json.dumps(context))

    def testBoundedToolPassesDetachedSixKeyEnvironmentWithoutAmbientCopy(self):
        experiment = self.experiment(); expected = dict(experiment.environment)
        with patch.object(bp.os,'environ',ObservedMapping({MARKER:object()},forbid_all=True)), \
             patch.object(bp.subprocess,'Popen',side_effect=OSError('memory spawn refusal')) as popen:
            with self.assertRaises(bp.ProcessFailure):
                bp.run(('/usr/bin/codesign','--verify','/synthetic-owned'),cwd=experiment.workspace.path,
                       environment=experiment.environment,timeout=1)
        self.assertEqual(popen.call_args.kwargs['env'],expected)
        self.assertIsNot(popen.call_args.kwargs['env'],experiment.environment)
        self.assertEqual(len(popen.call_args.kwargs['env']),6)
        self.assertNotIn(MARKER,popen.call_args.kwargs['env'])
        tree=ast.parse((HERE/'experiment_controller.py').read_text())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and ast.unparse(n.func)=='bp.run']
        self.assertEqual(len(calls),1)
        self.assertEqual(ast.unparse(next(k.value for k in calls[0].keywords if k.arg=='environment')),'self.environment')

    def testHistoricalDiagnosticStillReportsOptionalNameAsMismatch(self):
        keys = set(boot.STARTUP_KEYS)|{MARKER}
        summary = boot.startup_key_diagnostic(keys)
        self.assertTrue(summary['known_system_presence'][MARKER])
        record={'schema':1,'outcome':'keys_mismatch','environment_keys':summary}
        self.assertEqual(json.loads(observation.encode_record(record)[len(observation.PREFIX):]),record)
        self.assertEqual(observation.PROFILE_HASH,'9185bcf82855edff5a5e8eef9c63f67a6cd307aa9b8a7db4d35fde4a88dfab42')

    def testNewAnchorOnlyRepinsProfileAndKeepsBothWorkflowsAbsent(self):
        # Retain the historical method identity while explicitly checking both
        # repository states. The source guard separately rejects any other state.
        repo=HERE.parents[4]; folder=HERE.parent/'StageB'
        old=(folder/'owned-selected-folder-build.encoding-marker.yml.inert').read_bytes()
        self.assertEqual(hashlib.sha256(old).hexdigest(), '86d0f8ce0f81021bf3e6d70c2e499cf576e598a4851ddff782e0f57192ad836d')
        predecessor=(folder/'owned-selected-folder-build.encoding-attempt.yml.inert').read_bytes()
        self.assertEqual(hashlib.sha256(predecessor).hexdigest(), '443941896ee98159062a767719ffb020ba257ec966d732eefd8c8f08fb4f65c9')
        new=(repo/profile.TEMPLATE).read_bytes();raw=(HERE/'stage_b_profile.py').read_bytes()
        normal=raw.replace(b'BUILD_ONLY_ENABLED = True\n',b'BUILD_ONLY_ENABLED = False\n',1)
        self.assertIn(hashlib.sha256(normal).hexdigest().encode(),new)
        self.assertIs(type(profile.BUILD_ONLY_ENABLED),bool)
        self.assertEqual(profile.REF,'refs/heads/validation/owned-build-static-dependencies-once-20261013')
        if profile.BUILD_ONLY_ENABLED:
            self.assertEqual((repo/profile.WORKFLOW).read_bytes(),new)
        else:
            self.assertFalse((repo/profile.WORKFLOW).exists())
        self.assertFalse((repo/observation.WORKFLOW).exists())
        self.assertEqual(hashlib.sha256((HERE/'stage_b_bootstrap.py').read_bytes()).hexdigest(),dict(profile.MODULE_ROWS)['stage_b_bootstrap.py'])
        historical=(folder/'startup-key-observation.profile.inert').read_bytes()
        self.assertEqual(hashlib.sha256(historical).hexdigest(),observation.PROFILE_HASH)
        self.assertEqual(observation.decode_profile(historical,observation.PROFILE_HASH)['TEMPLATE'],
                         boot.RELATIVE+'/StageB/owned-selected-folder-build.environment-diagnostic.yml.inert')


if __name__=='__main__':unittest.main()
