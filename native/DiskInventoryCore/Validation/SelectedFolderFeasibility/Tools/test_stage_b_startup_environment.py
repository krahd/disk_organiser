"""Memory-only environment admission and static inert-shell regressions.

No shell fragment, /usr/bin/env, native command or workflow is executed.
"""
import ast
import json
from pathlib import Path
import re
import shlex
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import stage_b_bootstrap as boot


FIXED = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C', 'LC_ALL': 'C'}
IDENTITY = {
    'EXPECTED_DRIVER_SHA', 'GITHUB_EVENT_NAME', 'GITHUB_REPOSITORY', 'GITHUB_REF',
    'CREATED_REF', 'CREATED_REF_TYPE',
    'GITHUB_SHA', 'CHECKED_OUT_SHA', 'GITHUB_WORKFLOW_SHA', 'GITHUB_RUN_ATTEMPT',
    'GITHUB_WORKFLOW_REF', 'GITHUB_WORKSPACE', 'GITHUB_RUN_ID', 'ImageOS', 'ImageVersion'}
PYTHON = '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12'
TOOLS = 'native/DiskInventoryCore/Validation/SelectedFolderFeasibility/Tools/'


class StartupEnvironmentTests(unittest.TestCase):
    def environment(self):
        return {**{key:'identity' for key in IDENTITY}, **FIXED}

    def testExactAllowlistCopiesOnlyReviewedKeys(self):
        environment=self.environment()
        self.assertEqual(boot.STARTUP_KEYS, IDENTITY | FIXED.keys())
        self.assertEqual(boot.STARTUP_FIXED, FIXED)
        result=boot.startup_environment(environment)
        self.assertEqual(result,environment);self.assertIsNot(result,environment)
        environment['GITHUB_RUN_ID']='changed'
        self.assertEqual(result['GITHUB_RUN_ID'],'identity')

    def testEveryUnexpectedInheritedVariableRefuses(self):
        for key in ('PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT','PYTHONWARNINGS',
                    'PYTHONBREAKPOINT','PYTHONSAFEPATH','BASH_ENV','ENV','LD_PRELOAD',
                    'DYLD_INSERT_LIBRARIES','DYLD_LIBRARY_PATH','HTTP_PROXY','HTTPS_PROXY',
                    'ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy',
                    'GITHUB_TOKEN','ACTIONS_RUNTIME_TOKEN','ACTIONS_ID_TOKEN_REQUEST_TOKEN',
                    'SSH_AUTH_SOCK','AWS_SECRET_ACCESS_KEY','HOME','TMPDIR','GITHUB_OUTPUT'):
            with self.subTest(key=key):
                environment=self.environment();environment[key]='untrusted-value'
                with self.assertRaisesRegex(boot.Refusal,'startup environment keys'):
                    boot.startup_environment(environment)

    def testMissingKeysChangedFixedSettingsAndMalformedValuesRefuse(self):
        for key in IDENTITY | FIXED.keys():
            with self.subTest(missing=key):
                environment=self.environment();del environment[key]
                with self.assertRaises(boot.Refusal):boot.startup_environment(environment)
            for value in ('', 'x'*4097, 'a\0b', 1, b'bytes'):
                with self.subTest(key=key,value_type=type(value).__name__):
                    environment=self.environment();environment[key]=value
                    with self.assertRaises(boot.Refusal):boot.startup_environment(environment)
        for key in FIXED:
            with self.subTest(fixed=key):
                environment=self.environment();environment[key]='untrusted'
                with self.assertRaisesRegex(boot.Refusal,'fixed startup environment'):
                    boot.startup_environment(environment)

    def testDirtyEnvironmentRefusesBeforeWorkflowReadsOrOperationalImports(self):
        environment=self.environment();environment['HTTPS_PROXY']='untrusted-value'
        profile={'BUILD_ONLY_ENABLED':True,'PYTHON':PYTHON}
        with patch.object(boot,'read_source',return_value=b'profile') as read, \
             patch.object(boot,'decode_profile',return_value=profile), \
             patch.object(boot,'load_modules') as load, \
             patch.object(boot,'admit_sources') as admit, \
             patch.object(boot,'verify_dispatch') as dispatch, \
             patch.object(boot.sys,'flags',SimpleNamespace(isolated=1,no_site=1,dont_write_bytecode=1)), \
             patch.object(boot.sys,'version_info',(3,12,10)), \
             patch.object(boot.sys,'executable',PYTHON), \
             patch.object(boot.sys,'platform','darwin'), \
             patch.object(boot.os,'uname',return_value=SimpleNamespace(machine='arm64')), \
             patch.object(boot.os,'environ',environment):
            with self.assertRaisesRegex(boot.Refusal,'startup environment keys') as caught:
                boot.main('a'*64)
            self.assertEqual(caught.exception.key_diagnostic['unknown_count'], 1)
        self.assertEqual(read.call_count,1);dispatch.assert_not_called();admit.assert_not_called();load.assert_not_called()

    def mismatch(self, environment):
        with self.assertRaises(boot.StartupEnvironmentRefusal) as caught:
            boot.startup_environment(environment)
        self.assertIs(type(caught.exception), boot.StartupEnvironmentRefusal)
        self.assertEqual(str(caught.exception), 'startup environment keys')
        return caught.exception

    def testMissingDiagnosticNamesComeOnlyFromExactExpectedSet(self):
        self.assertEqual(boot.STARTUP_KNOWN_SYSTEM_KEYS,
                         ('LC_CTYPE', '__PYVENV_LAUNCHER__', '__CF_USER_TEXT_ENCODING', '_'))
        self.assertFalse(set(boot.STARTUP_KNOWN_SYSTEM_KEYS) & boot.STARTUP_KEYS)
        for key in sorted(boot.STARTUP_KEYS):
            with self.subTest(key=key):
                environment = self.environment(); del environment[key]
                diagnostic = self.mismatch(environment).key_diagnostic
                self.assertEqual(diagnostic['missing_expected'], [key])
                self.assertEqual(diagnostic['unexpected_count'], 0)
                self.assertEqual(diagnostic['unknown_count'], 0)
        diagnostic = self.mismatch({}).key_diagnostic
        self.assertEqual(diagnostic['missing_expected'], sorted(boot.STARTUP_KEYS))

    def testKnownSystemPresenceNeverAdmitsAnException(self):
        for key in boot.STARTUP_KNOWN_SYSTEM_KEYS:
            with self.subTest(key=key):
                environment = self.environment(); environment[key] = 'SECRET-VALUE'
                # The diagnostic itself grants nothing. Preserve this historical
                # method identity while explicitly testing the new admission rule.
                if key == '__CF_USER_TEXT_ENCODING': del environment['GITHUB_RUN_ID']
                diagnostic = self.mismatch(environment).key_diagnostic
                self.assertEqual(diagnostic['missing_expected'],
                                 ['GITHUB_RUN_ID'] if key == '__CF_USER_TEXT_ENCODING' else [])
                self.assertEqual(diagnostic['known_system_presence'],
                                 {name: name == key for name in boot.STARTUP_KNOWN_SYSTEM_KEYS})
                self.assertEqual(diagnostic['unexpected_count'], 1)
                self.assertEqual(diagnostic['unknown_count'], 0)
                self.assertNotIn('SECRET-VALUE', json.dumps(diagnostic))
        environment = {**self.environment(), **dict.fromkeys(boot.STARTUP_KNOWN_SYSTEM_KEYS, 'SECRET-VALUE')}
        diagnostic = self.mismatch(environment).key_diagnostic
        self.assertTrue(all(diagnostic['known_system_presence'].values()))
        self.assertEqual(diagnostic['unexpected_count'], 4)
        self.assertEqual(diagnostic['unknown_count'], 0)

    def testUnknownKeyNamesAndAllValuesAreAbsentFromDiagnosticAndException(self):
        for key in ('DO-NOT-LOG-THIS-KEY', 'sensitive' * 1024, 'private\nline', '\u00e9-secret', 123, b'secret-key'):
            with self.subTest(key_type=type(key).__name__):
                environment = self.environment(); environment[key] = 'DO-NOT-LOG-THIS-VALUE'
                error = self.mismatch(environment)
                diagnostic = error.key_diagnostic
                self.assertEqual(diagnostic['unexpected_count'], 1)
                self.assertEqual(diagnostic['unknown_count'], 1)
                self.assertEqual(error.args, ('startup environment keys',))
                self.assertEqual(set(vars(error)), {'key_diagnostic'})
                raw = json.dumps(boot.startup_refusal_record(error))
                for fragment in ('DO-NOT-LOG', 'sensitive', 'private', 'secret-key', '\u00e9-secret'):
                    self.assertNotIn(fragment, raw)

    def testDirtyKeySummaryNeverRequestsEnvironmentValues(self):
        class ValuesForbidden(dict):
            def __getitem__(self, key): raise AssertionError('environment value read')
            def items(self): raise AssertionError('environment items read')
            def values(self): raise AssertionError('environment values read')
        environment = ValuesForbidden(self.environment())
        environment['UNKNOWN'] = object()
        diagnostic = self.mismatch(environment).key_diagnostic
        self.assertEqual(diagnostic['unknown_count'], 1)

    def testDiagnosticCountsSaturateWithExplicitOverflowFlags(self):
        self.assertEqual(boot.STARTUP_DIAGNOSTIC_COUNT_CAP, 256)
        for count in (1, 255, 256, 257, 1024):
            with self.subTest(count=count):
                environment = {**self.environment(), **{'private-' + str(i): 'SECRET' for i in range(count)},
                               **dict.fromkeys(boot.STARTUP_KNOWN_SYSTEM_KEYS, 'SECRET')}
                diagnostic = self.mismatch(environment).key_diagnostic
                self.assertEqual(diagnostic['unexpected_count'], min(count + 4, 256))
                self.assertEqual(diagnostic['unexpected_count_capped'], count + 4 > 256)
                self.assertEqual(diagnostic['unknown_count'], min(count, 256))
                self.assertEqual(diagnostic['unknown_count_capped'], count > 256)
                self.assertTrue(all(diagnostic['known_system_presence'].values()))

    def testDiagnosticDoesNotRetainMutableEnvironmentOrOriginalKeySet(self):
        environment = self.environment(); environment['LC_CTYPE'] = ['SECRET']
        error = self.mismatch(environment)
        before = json.dumps(error.key_diagnostic, sort_keys=True)
        environment.clear(); environment['NEW-SECRET'] = 'NEW-VALUE'
        self.assertEqual(json.dumps(error.key_diagnostic, sort_keys=True), before)
        keys = {'LC_CTYPE'}; diagnostic = boot.startup_key_diagnostic(keys)
        keys.clear()
        self.assertTrue(diagnostic['known_system_presence']['LC_CTYPE'])
        self.assertNotIn('NEW-SECRET', before)

    def testRefusalRecordAddsSummaryOnlyForTheExactMismatchType(self):
        error = self.mismatch({})
        self.assertIs(boot.startup_refusal_record(error)['environment_keys'], error.key_diagnostic)
        other = boot.Refusal('unrelated refusal')
        other.key_diagnostic = {'SECRET': 'SECRET'}
        self.assertNotIn('environment_keys', boot.startup_refusal_record(other))
        class OtherMismatch(boot.StartupEnvironmentRefusal): pass
        self.assertNotIn('environment_keys', boot.startup_refusal_record(OtherMismatch(set())))

    def testMaximumDiagnosticShapeIsFixedPrimitiveAndBoundedJSON(self):
        error = self.mismatch({**dict.fromkeys(boot.STARTUP_KNOWN_SYSTEM_KEYS, 'SECRET' * 1000),
                               **{'unknown-' + str(i): object() for i in range(1024)}})
        diagnostic = error.key_diagnostic
        self.assertEqual(set(diagnostic), {'schema', 'missing_expected', 'unexpected_count',
                         'unexpected_count_capped', 'known_system_presence', 'unknown_count',
                         'unknown_count_capped'})
        self.assertIs(type(diagnostic['schema']), int); self.assertEqual(diagnostic['schema'], 1)
        for name in ('unexpected_count', 'unknown_count'):
            self.assertIs(type(diagnostic[name]), int)
        for name in ('unexpected_count_capped', 'unknown_count_capped'):
            self.assertIs(type(diagnostic[name]), bool)
        self.assertTrue(all(type(value) is bool for value in diagnostic['known_system_presence'].values()))
        self.assertEqual(diagnostic['missing_expected'], sorted(boot.STARTUP_KEYS))
        with patch.object(boot.sys, 'executable', 'x' * 512), \
             patch.object(boot.sys, 'platform', 'p' * 16), \
             patch.object(boot.sys, 'version_info', (65535, 65535, 65535)):
            record = boot.startup_refusal_record(error)
        raw = json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        self.assertLessEqual(len(raw), 2048)
        self.assertEqual(json.loads(raw)['environment_keys'], diagnostic)
        self.assertNotIn(b'unknown-', raw); self.assertNotIn(b'SECRET', raw)

    def testCLIRefusalSerialisesOnlyTheFixedReporterWithoutFreshEnvironmentRead(self):
        tree = ast.parse(Path(boot.__file__).read_text())
        entry = next(node for node in tree.body if isinstance(node, ast.If) and
                     isinstance(node.test, ast.Compare) and ast.unparse(node.test) == "__name__ == '__main__'")
        handler = next(node for node in ast.walk(entry) if isinstance(node, ast.ExceptHandler))
        reporters = [node for node in ast.walk(handler) if isinstance(node, ast.Call) and
                     isinstance(node.func, ast.Name) and node.func.id == 'startup_refusal_record']
        self.assertEqual(len(reporters), 1)
        self.assertEqual(ast.unparse(reporters[0]), 'startup_refusal_record(error)')
        self.assertNotIn('os.environ', ast.unparse(handler))
        self.assertNotIn('startup_environment', ast.unparse(handler))

    def shell(self):
        raw=(Path(__file__).parents[1]/'StageB/owned-selected-folder-build.encoding-attempt.yml.inert').read_text()
        run=raw.split('        run: |\n',1)[1].split('      - name:',1)[0]
        return '\n'.join(line[10:] for line in run.splitlines())

    def launch(self, shell, variable):
        matches=re.findall(r'^'+variable+r'="\$\((.*?)\)"$',shell,re.M|re.S)
        self.assertEqual(len(matches),1)
        raw=matches[0].replace('\\\n',' ')
        tokens=shlex.split(raw)
        self.assertEqual(tokens[:2],['/usr/bin/env','-i'])
        interpreter=tokens.index(PYTHON)
        assignments=tokens[2:interpreter]
        names=[entry.split('=',1)[0] for entry in assignments]
        self.assertEqual(len(names),len(set(names)))
        return raw,dict(entry.split('=',1) for entry in assignments),tokens[interpreter:]

    def testBothFixedPythonLaunchesUseExactEnvIAllowlists(self):
        shell=self.shell()
        self.assertEqual(shell.count('/usr/bin/env -i'),2)
        self.assertEqual(shell.count(PYTHON),2)
        raw,environment,command=self.launch(shell,'terminal')
        expected={key:'$'+key for key in IDENTITY}
        expected['CHECKED_OUT_SHA']='$checked_out_sha';expected.update(FIXED)
        self.assertEqual(environment,expected)
        self.assertEqual(command[:5],[PYTHON,'-I','-S','-B',TOOLS+'stage_b_bootstrap.py'])
        self.assertEqual(len(command),6);self.assertRegex(command[-1],r'^[0-9a-f]{64}$')
        for key,value in expected.items():
            if value.startswith('$'):self.assertIn(key+'="'+value+'"',raw)
        raw,environment,command=self.launch(shell,'report_path')
        expected={**FIXED,'BUILD_TERMINAL':'$terminal','GITHUB_RUN_ID':'$GITHUB_RUN_ID','GITHUB_SHA':'$GITHUB_SHA'}
        self.assertEqual(environment,expected)
        self.assertEqual(command,[PYTHON,'-I','-S','-B',TOOLS+'stage_b_upload.py'])
        for key,value in expected.items():
            if value.startswith('$'):self.assertIn(key+'="'+value+'"',raw)
        self.assertNotIn('export ',shell);self.assertNotIn('${{',shell)
        self.assertIn('checked_out_sha="$(/usr/bin/git rev-parse --verify HEAD)"',shell)
        self.assertIn('result=$?\nset -e\nprintf',shell)
        self.assertIn('"$GITHUB_OUTPUT"',shell);self.assertTrue(shell.endswith('exit "$result"'))

    def testMainPassesOnlySanitisedMappingToDispatch(self):
        tree=ast.parse(Path(boot.__file__).read_text())
        main=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main')
        assignments=[node for node in ast.walk(main) if isinstance(node,ast.Assign) and
                     any(isinstance(target,ast.Name) and target.id=='environment' for target in node.targets)]
        self.assertEqual(len(assignments),1)
        self.assertEqual(ast.unparse(assignments[0].value),'startup_environment(os.environ)')
        dispatch=next(node for node in ast.walk(main) if isinstance(node,ast.Call) and
                      isinstance(node.func,ast.Name) and node.func.id=='verify_dispatch')
        self.assertEqual(ast.unparse(dispatch.args[0]),'environment')


if __name__=='__main__':unittest.main()
