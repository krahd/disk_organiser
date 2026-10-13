"""Memory/mock and source checks only. Never starts the diagnostic or a shell."""
import ast
from collections.abc import Mapping
from contextlib import ExitStack, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import stage_b_bootstrap as boot
import startup_key_observation as probe

HERE = Path(__file__).parent
ROOT = HERE.parents[4]


class KeyMapping(Mapping):
    def __init__(self, keys): self.keys_seen = list(keys); self.iterations = 0
    def __iter__(self):
        self.iterations += 1
        return iter(self.keys_seen)
    def __len__(self): return len(self.keys_seen)
    def __getitem__(self, key): raise AssertionError('environment value access')


class StartupOnlyObservationTests(unittest.TestCase):
    def arguments(self):
        sha = 'a' * 40
        return ['b' * 64, sha, probe.REF.removeprefix('refs/heads/'), 'branch', 'create',
                'krahd/disk_organiser', probe.REF, sha, sha, sha, '1',
                'krahd/disk_organiser/' + probe.WORKFLOW + '@' + probe.REF,
                probe.CHECKOUT, '123', 'macos15', '20261012.1']

    def context(self, environment=None):
        environment = environment if environment is not None else KeyMapping(probe.STARTUP_KEYS)
        stack = ExitStack()
        self.addCleanup(stack.close)
        raw = (HERE / 'startup_key_observation.py').read_bytes()
        args = self.arguments(); args[0] = hashlib.sha256(raw).hexdigest()
        def read(path, limit, **kwargs):
            kwargs.get('check', lambda: None)()
            return raw if path == probe.ENTRY else b'fixed'
        read_mock = stack.enter_context(patch.object(probe, 'read_source', side_effect=read))
        stack.enter_context(patch.object(probe, 'decode_profile', return_value={'BUILD_ONLY_ENABLED':False, 'PYTHON':'fixed'}))
        identity = stack.enter_context(patch.object(probe, 'interpreter_identity', return_value={}))
        system = stack.enter_context(patch.object(probe, 'system_version', return_value={}))
        stack.enter_context(patch.object(probe.os, 'environ', environment))
        stack.enter_context(patch.object(probe.time, 'monotonic', return_value=10.0))
        return args, environment, read_mock, identity, system

    def testExactKeysObserveRealMappingOnceWithoutValues(self):
        args, env, read, identity, system = self.context()
        result = probe.observe(args)
        self.assertEqual(result['outcome'], 'keys_match'); self.assertEqual(env.iterations, 1)
        self.assertEqual(result['environment_keys'], boot.startup_key_diagnostic(set(probe.STARTUP_KEYS)))
        self.assertEqual([x.args[0] for x in read.call_args_list],
                         [probe.ENTRY, probe.WORKFLOW, probe.TEMPLATE, probe.RELATIVE+'/Tools/stage_b_profile.py'])
        identity.assert_called_once(); system.assert_called_once()

    def testActualLateRuntimeMutationIsObservedNotReconstructed(self):
        args, env, _, identity, system = self.context()
        identity.side_effect = lambda _: env.keys_seen.append('LC_CTYPE')
        system.side_effect = lambda **_: env.keys_seen.append('DO-NOT-EMIT-UNKNOWN')
        result = probe.observe(args)
        self.assertEqual(result['outcome'], 'keys_mismatch'); self.assertEqual(env.iterations,1)
        self.assertTrue(result['environment_keys']['known_system_presence']['LC_CTYPE'])
        self.assertEqual(result['environment_keys']['unknown_count'],1)
        self.assertNotIn('DO-NOT-EMIT', probe.encode_record(result))

    def testEachMissingExpectedKeyIsFixedNameOnly(self):
        for missing in probe.STARTUP_KEYS:
            with self.subTest(missing=missing):
                args, env, *_ = self.context(KeyMapping(probe.STARTUP_KEYS-{missing}))
                record=probe.observe(args)
                self.assertEqual(record['outcome'],'keys_mismatch')
                self.assertEqual(record['environment_keys']['missing_expected'],[missing])
                self.assertEqual(env.iterations,1)

    def testEachKnownKeyStillReportsMismatch(self):
        for key in probe.STARTUP_KNOWN_SYSTEM_KEYS:
            args, env, *_=self.context(KeyMapping([*probe.STARTUP_KEYS,key]))
            record=probe.observe(args)
            self.assertEqual(record['outcome'],'keys_mismatch')
            self.assertEqual(record['environment_keys']['known_system_presence'],
                             {k:k==key for k in probe.STARTUP_KNOWN_SYSTEM_KEYS})

    def testUnknownUnicodeLongAndPrivateKeysNeverLeaveSummary(self):
        for key in ['NEVER-SHARE', 'private\nname', 'é-private', 'private'*8192]:
            args, env, *_=self.context(KeyMapping([*probe.STARTUP_KEYS,key]))
            record=probe.observe(args); raw=probe.encode_record(record)
            self.assertEqual(record['environment_keys']['unknown_count'],1)
            for word in ['NEVER-SHARE','private','é']: self.assertNotIn(word,raw)

    def testCountBoundaryAndMaximumRecord(self):
        for count in [0,1,255,256,257,1500]:
            keys=list(probe.STARTUP_KNOWN_SYSTEM_KEYS)+['private'+str(i) for i in range(count)]
            args, env, *_=self.context(KeyMapping(keys))
            record=probe.observe(args); d=record['environment_keys']
            self.assertEqual(d['unknown_count'],min(count,256));self.assertEqual(d['unknown_count_capped'],count>256)
            self.assertEqual(d['unexpected_count'],min(count+4,256))
            self.assertEqual(d['unexpected_count_capped'],count+4>256)
            self.assertLessEqual(len((probe.encode_record(record)+'\n').encode()),2048)
            self.assertEqual(d['missing_expected'],sorted(probe.STARTUP_KEYS))

    def testSuccessfulRecordHasOnlyExactPrimitiveSchema(self):
        args,*_=self.context();r=probe.observe(args)
        self.assertEqual(set(r),{'schema','outcome','environment_keys'})
        self.assertIs(type(r['schema']),int)
        d=r['environment_keys']
        self.assertEqual(set(d),{'schema','missing_expected','unexpected_count','unexpected_count_capped',
            'known_system_presence','unknown_count','unknown_count_capped'})
        self.assertIs(type(d['unknown_count']),int);self.assertIs(type(d['unexpected_count']),int)
        self.assertTrue(all(type(v) is bool for v in d['known_system_presence'].values()))

    def testSummaryDetachedFromMappingMutation(self):
        args,env,*_=self.context();r=probe.observe(args);before=probe.encode_record(r)
        env.keys_seen[:]=['PRIVATE'];self.assertEqual(probe.encode_record(r),before)

    def testEveryDispatchIdentityRejectsBeforeObservation(self):
        for index in range(1,len(probe.ARGUMENT_NAMES)):
            args,env,read,*_=self.context();args[index]='WRONG'
            self.assertEqual(probe.observe(args),probe.inconclusive('arguments'))
            self.assertEqual(env.iterations,0);read.assert_not_called()

    def testCaseVariantEventRefAndAttemptRefuseBeforeRead(self):
        for index,value in [(2,'Validation/startup-keys-once-20261013'),(6,probe.REF.upper()),(10,'02'),
                            (5,'Krahd/disk_organiser'),(4,'CREATE')]:
            args,env,read,*_=self.context();args[index]=value
            self.assertEqual(probe.observe(args)['reason'],'arguments')
            read.assert_not_called();self.assertEqual(env.iterations,0)

    def testSchedulerCaseFoldCanAllocateButCoherentVariantRefuses(self):
        args,env,read,*_=self.context()
        variant='Validation/startup-keys-once-20261013'
        self.assertEqual(variant.lower(),probe.REF.removeprefix('refs/heads/').lower())
        args[2]=variant;args[6]='refs/heads/'+variant
        args[11]='krahd/disk_organiser/'+probe.WORKFLOW+'@'+args[6]
        self.assertEqual(probe.observe(args),probe.inconclusive('arguments'))
        self.assertEqual(env.iterations,0);read.assert_not_called()

    def testArgumentsTypeLengthAsciiAndBoundsRefuse(self):
        for bad in [None,(),[],self.arguments()+['extra']]:
            self.assertEqual(probe.observe(bad)['reason'],'arguments')
        for value in [True,1,'','x'*4097,'a\0b','a\nb','a\rb','é']:
            args=self.arguments();args[15]=value
            self.assertEqual(probe.observe(args)['reason'],'arguments')

    def testSourceMismatchRefusesBeforeRuntimeAndCapture(self):
        args,env,read,identity,system=self.context();args[0]='c'*64
        self.assertEqual(probe.observe(args)['reason'],'source')
        identity.assert_not_called();system.assert_not_called();self.assertEqual(env.iterations,0)

    def testUnequalWorkflowAndTemplateRefuseBeforeCapture(self):
        args,env,read,identity,_=self.context();old=read.side_effect
        read.side_effect=lambda p,*a,**k:b'different' if p==probe.TEMPLATE else old(p,*a,**k)
        self.assertEqual(probe.observe(args)['reason'],'source')
        identity.assert_not_called();self.assertEqual(env.iterations,0)

    def testActiveBuildProfileRefusesBeforeCapture(self):
        args,env,_,identity,_=self.context()
        with patch.object(probe,'decode_profile',return_value={'BUILD_ONLY_ENABLED':True}):
            self.assertEqual(probe.observe(args)['reason'],'profile')
        identity.assert_not_called();self.assertEqual(env.iterations,0)

    def testRuntimeAndSystemFailuresEmitFixedReasonsOnly(self):
        for which,phase in [('interpreter_identity','runtime'),('system_version','system')]:
            args,env,*_=self.context()
            with patch.object(probe,which,side_effect=RuntimeError('PRIVATE ENV VALUE')):
                record=probe.observe(args)
            self.assertEqual(record,probe.inconclusive(phase));self.assertEqual(env.iterations,0)
            self.assertNotIn('PRIVATE',probe.encode_record(record))

    def testMonotonicFailureRefusesBeforeCapture(self):
        for times in [[float('nan')],[10,9],[10,55]]:
            args,env,*_=self.context()
            with patch.object(probe.time,'monotonic',side_effect=times):record=probe.observe(args)
            self.assertEqual(record['outcome'],'inconclusive');self.assertEqual(env.iterations,0)

    def testActualInterpreterShapeAndFlagsRetainFailClosedChecks(self):
        profile={'PYTHON':'/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12'}
        with patch.object(probe.sys,'executable',profile['PYTHON']),patch.object(probe.sys,'version_info',(3,12,10)), \
             patch.object(probe.sys,'platform','darwin'),patch.object(probe.os,'uname',return_value=SimpleNamespace(machine='arm64')), \
             patch.object(probe.sys,'flags',SimpleNamespace(isolated=1,no_site=1,dont_write_bytecode=1)):
            self.assertEqual(probe.interpreter_identity(profile)['flags'],{'isolated':1,'no_site':1,'dont_write_bytecode':1})
            for bad in [True,False,0,2,'1']:
                with patch.object(probe.sys,'flags',SimpleNamespace(isolated=bad,no_site=1,dont_write_bytecode=1)):
                    with self.assertRaises(probe.Refusal):probe.interpreter_identity(profile)
            for key,value in [('executable','/wrong'),('version_info',(3,12,11)),('platform','linux')]:
                with patch.object(probe.sys,key,value):
                    with self.assertRaises(probe.Refusal):probe.interpreter_identity(profile)

    def testCliHasOneBoundedRecordAndTerminalExitForBothBranches(self):
        for keys,code,outcome in [(probe.STARTUP_KEYS,0,'keys_match'),([*probe.STARTUP_KEYS,'PRIVATE'],2,'keys_mismatch')]:
            args,*_=self.context(KeyMapping(keys));out=io.StringIO()
            with redirect_stdout(out):actual=probe.cli(args)
            self.assertEqual(actual,code);self.assertEqual(len(out.getvalue().splitlines()),1)
            self.assertEqual(json.loads(out.getvalue()[len(probe.PREFIX):])['outcome'],outcome)
            self.assertLessEqual(len(out.getvalue().encode()),2048);self.assertNotIn('PRIVATE',out.getvalue())

    def testNoArgumentCliOnlyFixedInconclusiveRecord(self):
        out=io.StringIO()
        with redirect_stdout(out):code=probe.cli([])
        self.assertEqual(code,2)
        self.assertEqual(json.loads(out.getvalue()[len(probe.PREFIX):]),probe.inconclusive('arguments'))

    def testEncodingFailureUsesFixedBoundedFallback(self):
        for bad in [{'private':object()},{'private':'x'*3000},{'private':'SHORT-SECRET'},
                    {'schema':1,'outcome':'inconclusive','reason':'PRIVATE'},
                    {'schema':True,'outcome':'inconclusive','reason':'source'}]:
            line=probe.encode_record(bad)
            self.assertNotIn('private',line);self.assertEqual(json.loads(line[len(probe.PREFIX):]),probe.inconclusive('output'))

    def testInjectedOutputNamesValuesTypesAndContradictionsUseFixedFallback(self):
        args,*_=self.context();original=probe.observe(args)
        variants=[]
        for change in [lambda r:r.update(extra='PRIVATE'),
                       lambda r:r['environment_keys']['missing_expected'].append('PRIVATE'),
                       lambda r:r['environment_keys']['known_system_presence'].update(PRIVATE=True),
                       lambda r:r['environment_keys'].update(unknown_count=True),
                       lambda r:r['environment_keys'].update(unknown_count=5),
                       lambda r:r['environment_keys'].update(unknown_count_capped=True)]:
            r=json.loads(json.dumps(original));change(r);variants.append(r)
        for r in variants:
            line=probe.encode_record(r)
            self.assertEqual(json.loads(line[len(probe.PREFIX):]),probe.inconclusive('output'))
            self.assertNotIn('PRIVATE',line)

    def testReadFailureAndObservedIterationFailureHaveNoExceptionLeak(self):
        args,env,read,*_=self.context();read.side_effect=OSError('PRIVATE PATH')
        self.assertEqual(probe.observe(args),probe.inconclusive('source'));self.assertEqual(env.iterations,0)
        class Broken(KeyMapping):
            def __iter__(self):raise ValueError('PRIVATE KEY')
        args,*_=self.context(Broken([]));record=probe.observe(args)
        self.assertEqual(record,probe.inconclusive('observation'))
        self.assertNotIn('PRIVATE',probe.encode_record(record))

    def testSharedImportsAndNamedHelpersAreByteExact(self):
        a=(HERE/'stage_b_bootstrap.py').read_text();b=(HERE/'startup_key_observation.py').read_text()
        def chunks(s):
            tree=ast.parse(s);return {getattr(n,'name',None):ast.get_source_segment(s,n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        aa,bb=chunks(a),chunks(b)
        for name in ['Refusal','require','startup_key_diagnostic','interpreter_identity','_stamp','read_source','decode_profile','system_version']:
            self.assertEqual(aa[name],bb[name],name)
        imports=lambda s:[ast.get_source_segment(s,n) for n in ast.parse(s).body if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertEqual(imports(a),imports(b))
        self.assertEqual(probe.STARTUP_KEYS,boot.STARTUP_KEYS)
        self.assertEqual(probe.STARTUP_KNOWN_SYSTEM_KEYS,boot.STARTUP_KNOWN_SYSTEM_KEYS)

    def testEntryContainsNoOperationalMainImportOrSubprocess(self):
        s=(HERE/'startup_key_observation.py').read_text();tree=ast.parse(s)
        names={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        self.assertFalse(names & {'main','load_modules','admit_sources','verify_dispatch','startup_environment'})
        for n in ast.walk(tree):
            if isinstance(n,ast.Call):
                called=ast.unparse(n.func)
                self.assertNotIn(called,{'exec','eval','compile','__import__','os.system','os.fork','os.spawn','subprocess.run','open'})
                self.assertFalse(called.startswith(('subprocess.','importlib.')))
        self.assertEqual(s.count('set(os.environ)'),1)
        self.assertNotRegex(s,r'os\.environ\s*\[')

    def testWorkflowCopiesExactAndHasOnlyCheckoutAndOneObservation(self):
        template=(ROOT/probe.TEMPLATE).read_text();active=ROOT/probe.WORKFLOW
        # Both reviewed repository states are intentional: exact active bytes
        # before the one shot, or absent after terminal deactivation.
        if active.exists():self.assertEqual(active.read_text(),template)
        workflow=template
        self.assertEqual(workflow.count('      - '),2)
        self.assertIn('timeout-minutes: 5',workflow);self.assertEqual(workflow.count('timeout-minutes: 1'),2)
        self.assertIn('runs-on: macos-15',workflow)
        self.assertIn('permissions:\n  contents: read',workflow)
        self.assertNotIn('upload-artifact',workflow);self.assertNotIn('secrets.',workflow)
        self.assertNotIn('workflow_dispatch',workflow);self.assertNotIn('matrix:',workflow)
        self.assertIn('persist-credentials: false',workflow)
        digest=hashlib.sha256((HERE/'startup_key_observation.py').read_bytes()).hexdigest()
        self.assertEqual(workflow.count(digest),2)
        tokens=shlex.split(workflow.split('          exec /usr/bin/env -i ',1)[1].replace(chr(92)+chr(10), ''))
        path=tokens.index('/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12')
        self.assertEqual({x.split('=',1)[0] for x in tokens[:path]},set(probe.STARTUP_KEYS))
        self.assertEqual(tokens[path+1:path+4],['-I','-S','-B'])
        self.assertEqual(len(tokens[path+5:]),len(probe.ARGUMENT_NAMES))
        self.assertEqual(tokens[path+5],digest)

    def testExistingBuildProfileAndHistoricalAnchorsStayDisabled(self):
        raw=(HERE/'stage_b_profile.py').read_bytes()
        historical=(HERE.parent/'StageB/startup-key-observation.profile.inert').read_bytes()
        self.assertEqual(hashlib.sha256(historical).hexdigest(),probe.PROFILE_HASH)
        self.assertFalse(probe.decode_profile(historical,probe.PROFILE_HASH)['BUILD_ONLY_ENABLED'])
        # The consumed diagnostic keeps its original pin and refuses this new
        # profile. Its executed evidence is never relabelled as current runtime.
        self.assertNotEqual(raw,historical)
        with self.assertRaisesRegex(probe.Refusal,'profile hash mismatch'):
            probe.decode_profile(raw,probe.PROFILE_HASH)
        values={n.targets[0].id:ast.literal_eval(n.value) for n in ast.parse(raw).body if isinstance(n,ast.Assign)}
        self.assertIs(type(values['BUILD_ONLY_ENABLED']),bool)
        self.assertEqual(values['REF'],'refs/heads/validation/owned-build-encoding-once-20261013')
        if values['BUILD_ONLY_ENABLED']:
            self.assertEqual((ROOT/values['WORKFLOW']).read_bytes(),(ROOT/values['TEMPLATE']).read_bytes())
        else:
            self.assertFalse((ROOT/values['WORKFLOW']).exists())
        self.assertFalse((ROOT/probe.WORKFLOW).exists())
        self.assertNotEqual(probe.REF,values['REF'])
        self.assertEqual(len(list((HERE.parent/'StageB').glob('owned-selected-folder-build*.yml.inert'))),6)


if __name__=='__main__':unittest.main()
