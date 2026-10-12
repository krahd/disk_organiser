"""Memory-only environment admission and static inert-shell regressions.

No shell fragment, /usr/bin/env, native command or workflow is executed.
"""
import ast
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
PYTHON = '/Users/runner/hostedtoolcache/Python/3.12.10/arm64/bin/python3'
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
             patch.object(boot,'verify_dispatch') as dispatch, \
             patch.object(boot.sys,'flags',SimpleNamespace(isolated=1,no_site=1,dont_write_bytecode=1)), \
             patch.object(boot.sys,'version_info',(3,12,10)), \
             patch.object(boot.sys,'executable',PYTHON), \
             patch.object(boot.sys,'platform','darwin'), \
             patch.object(boot.os,'uname',return_value=SimpleNamespace(machine='arm64')), \
             patch.object(boot.os,'environ',environment):
            with self.assertRaisesRegex(boot.Refusal,'startup environment keys'):
                boot.main('a'*64)
        self.assertEqual(read.call_count,1);dispatch.assert_not_called();load.assert_not_called()

    def shell(self):
        raw=(Path(__file__).parents[1]/'StageB/owned-selected-folder-build.create.yml.inert').read_text()
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
