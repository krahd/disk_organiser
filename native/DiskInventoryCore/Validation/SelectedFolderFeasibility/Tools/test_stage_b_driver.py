"""Memory/mock-only admission, startup and orchestration regressions."""
from contextlib import ExitStack, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import ast
import hashlib
import json
import unittest

import probe_contract as pc
import experiment_controller as ec
import stage_b_admission as ba
import stage_b_bootstrap as boot
import stage_b_driver as driver
import stage_b_profile as profile
import stage_b_receipt as receipt
from test_experiment_controller import model


class AdmissionTests(unittest.TestCase):
    def testDisabledOrForgedAdmissionCannotCreate(self):
        with patch.object(profile, 'BUILD_ONLY_ENABLED', False), \
             patch.object(ec.ob.OwnedBuild, 'create') as create:
            with self.assertRaises(pc.Refusal): ba._issue(0)
            for value in (object(), {}, 'approved', True):
                with self.assertRaises(pc.Refusal): ec.Experiment.prepare('a'*40, {}, admission=value)
            create.assert_not_called()

    def testSingleUseOwnerAndThreadBeforeAnyTool(self):
        with patch.object(profile, 'BUILD_ONLY_ENABLED', True):
            admission = ba._issue(0, lambda: 1)
            admission.consume(profile.HOST_SOURCE_COMMIT, profile.HOST_ROWS)
            with self.assertRaises(pc.Refusal): admission.consume(profile.HOST_SOURCE_COMMIT, profile.HOST_ROWS)
            subject, _, _ = model(); admission.attach(subject)
            with self.assertRaises(pc.Refusal): admission.begin(object())
            with patch.object(ba.threading, 'get_ident', return_value=admission.thread+1):
                with self.assertRaises(pc.Refusal): admission.begin(subject)
            admission.begin(subject); admission.stop()
            with self.assertRaises(pc.Refusal): admission.begin(subject)
            admission.retire(); self.assertIsNone(admission.owner)

    def testSourceMismatchConsumesAndCannotBeReused(self):
        with patch.object(profile, 'BUILD_ONLY_ENABLED', True):
            admission = ba._issue(0, lambda: 1)
            with self.assertRaises(pc.Refusal): admission.consume('b'*40, profile.HOST_ROWS)
            with self.assertRaises(pc.Refusal): admission.consume(profile.HOST_SOURCE_COMMIT, profile.HOST_ROWS)

    def testDeadlineAndBackwardsClockBeforeCreation(self):
        for now in (720, float('nan'), -1):
            with patch.object(profile, 'BUILD_ONLY_ENABLED', True):
                admission=ba._issue(0, lambda: now)
                with self.assertRaises(pc.Refusal): admission.consume(profile.HOST_SOURCE_COMMIT, profile.HOST_ROWS)
        with patch.object(profile, 'BUILD_ONLY_ENABLED', True):
            clock=Mock(side_effect=[2,1]); admission=ba._issue(0,clock)
            admission.consume(profile.HOST_SOURCE_COMMIT,profile.HOST_ROWS)
            with self.assertRaises(pc.Refusal): admission.work_check()

    def testBAdmissionNeverEnablesC(self):
        subject, inspection, _=model()
        with patch.object(profile,'BUILD_ONLY_ENABLED',True):
            admission=ba._issue(0,lambda:1);admission.consume(profile.HOST_SOURCE_COMMIT,profile.HOST_ROWS)
            admission.attach(subject);subject._build_admission=admission
            with patch.object(subject,'_observe') as observe:
                with self.assertRaisesRegex(pc.Refusal,'Stage C closed'):subject.run_c(inspection)
                observe.assert_not_called()
            subject.close()

    def testPreparationPreservesFirstFailureAndBothRetirements(self):
        files={name:b'x' for name in ['Probe.xcodeproj/project.pbxproj','Probe.xcodeproj/xcshareddata/xcschemes/OwnedFolderProbe.xcscheme',
            'Host/main.swift','Host/host.entitlements.inert.plist','Generated/ProbeSeal.swift','Generated/fixture.json',
            'Generated/ProbeBuild.xcconfig','UITests/SelectionProbeUITests.swift']}
        workspace=Mock();fixture=Mock();fixture.claim=b'{}';workspace.products_path='/private/tmp/disk-selection-build-abc/Products'
        original=OSError('first write failure');workspace.close.side_effect=OSError('second close')
        with patch.object(profile,'BUILD_ONLY_ENABLED',True),patch.object(profile,'HOST_ROWS',ec._source_files(files)), \
             patch.object(ec.ob.OwnedBuild,'create',return_value=workspace),patch.object(ec.fi,'create_owned_fixture',return_value=fixture), \
             patch.object(ec.fi,'render_claimed_inputs',return_value={}),patch.object(ec,'_write_inputs',side_effect=original):
            admission=ba._issue(0,lambda:1)
            with self.assertRaises(ec.PreparationFailure) as result:ec.Experiment.prepare(profile.HOST_SOURCE_COMMIT,files,admission=admission)
        self.assertIs(result.exception.original,original);fixture.close.assert_called_once();workspace.close.assert_called_once()
        self.assertEqual(result.exception.dispositions,{'fixture':'closed','workspace':'unproved:OSError'})
        self.assertEqual(admission.state,'retired')

    def testAdmittedControllerUsesAll31ExactCommandsWithParsedObservations(self):
        # Historical method identity retained; one static slot extends the original 31.
        from test_native_observations import tool as observed_tool
        subject, inspection, _ = model(); subject.state='prepared'
        def tool(arguments, **kw):
            if 'build-for-testing' in arguments or '--force' in arguments:
                return ec.bp.ProcessResult(arguments,b'build/sign model',b'',0,True,False,'',True)
            return observed_tool(arguments, **kw)
        with patch.object(ec.no,'inspector_identity',return_value=(0,)*8),patch.object(profile,'BUILD_ONLY_ENABLED',True), patch.object(ec,'_verify_inputs'), \
             patch.object(ec,'_write_bound_configuration'), patch.object(ec.ob,'freeze',return_value=inspection.freeze), \
             patch.object(subject,'_configuration_name',return_value='Owned.xctestrun'), \
             patch.object(ec.bp,'run',side_effect=tool) as run:
            admission=ba._issue(0,lambda:1);admission.consume(profile.HOST_SOURCE_COMMIT,profile.HOST_ROWS)
            admission.attach(subject);subject._build_admission=admission
            result=subject.inspect_b()
            self.assertEqual(run.call_count,32);self.assertEqual(admission.guard.count,32)
            self.assertEqual(admission.state,'complete');self.assertEqual(subject.state,'inspected')
            self.assertEqual(len(result.preparation_log_digests),32)
            self.assertTrue(workspace_reads := subject.workspace.read_configuration.call_args_list)
            self.assertTrue(all(call.kwargs.get('check') == admission.work_check for call in workspace_reads))
            with self.assertRaises(pc.Refusal):subject.run_c(result)
            subject.close()

    def testBadVersionPreflightNeverBuildsOrSigns(self):
        import bounded_process as bp
        subject,_,_=model();subject.state='prepared';subject.workspace.inventory.return_value=()
        def bad(args,**kw):return bp.ProcessResult(args,b'Xcode unexpected',b'',0,True,False,'',True)
        with patch.object(profile,'BUILD_ONLY_ENABLED',True),patch.object(ec,'_verify_inputs'),patch.object(ec.bp,'run',side_effect=bad) as run:
            admission=ba._issue(0,lambda:1);admission.consume(profile.HOST_SOURCE_COMMIT,profile.HOST_ROWS)
            admission.attach(subject);subject._build_admission=admission
            with self.assertRaises(pc.Refusal):subject.inspect_b()
            self.assertEqual(run.call_count,3)  # fixed version trio observed; no build/sign command
            self.assertTrue(all('build-for-testing' not in c.args[0] for c in run.call_args_list))
            self.assertEqual(subject.state,'failed');subject.close()


class BootstrapTests(unittest.TestCase):
    def profile(self):
        raw=(Path(__file__).parent/'stage_b_profile.py').read_bytes()
        # This fixture exercises both states, regardless of the checked-out flag.
        raw=raw.replace(b'BUILD_ONLY_ENABLED = True\n', b'BUILD_ONLY_ENABLED = False\n', 1)
        raw=raw.replace(('EXPECTED_RUN_NUMBER = '+str(profile.EXPECTED_RUN_NUMBER)+'\n').encode(),
                        b'EXPECTED_RUN_NUMBER = 17\n', 1)
        return raw,hashlib.sha256(raw).hexdigest()

    def testOnlyLiteralFlagNormalisationIsPermitted(self):
        raw,digest=self.profile()
        self.assertFalse(boot.decode_profile(raw,digest)['BUILD_ONLY_ENABLED'])
        self.assertTrue(boot.decode_profile(raw.replace(b'BUILD_ONLY_ENABLED = False',b'BUILD_ONLY_ENABLED = True'),digest)['BUILD_ONLY_ENABLED'])
        for changed in (raw+b'X = 1\n',raw.replace(profile.HOST_SOURCE_COMMIT.encode(), ('0' if profile.HOST_SOURCE_COMMIT[0] != '0' else '1').encode()+profile.HOST_SOURCE_COMMIT[1:].encode(), 1),raw+b'import os\n',raw.replace(b'= False',b'= 1',1)):
            self.assertNotEqual(changed, raw)
            with self.assertRaises((boot.Refusal,ValueError)):boot.decode_profile(changed,digest)

    def testDisabledStartupDoesNotReadOtherFilesOrImportOwners(self):
        raw,digest=self.profile()
        with patch.object(boot,'read_source',return_value=raw) as read,patch.object(boot,'load_modules') as load, \
             patch.object(boot.sys,'flags',SimpleNamespace(isolated=1,no_site=1,dont_write_bytecode=1)):
            with self.assertRaisesRegex(boot.Refusal,'disabled'):boot.main(digest, '17')
        self.assertEqual(read.call_count,1);load.assert_not_called()

    def identity(self):
        p=vars(profile);sha='a'*40
        env={'EXPECTED_DRIVER_SHA':sha,'GITHUB_SHA':sha,'CHECKED_OUT_SHA':sha,'GITHUB_WORKFLOW_SHA':sha,
             'GITHUB_EVENT_NAME':'create','CREATED_REF_TYPE':'branch','CREATED_REF':profile.REF.removeprefix('refs/heads/'),'GITHUB_REPOSITORY':profile.REPOSITORY,'GITHUB_REF':profile.REF,
             'GITHUB_RUN_ATTEMPT':'1','GITHUB_RUN_ID':'123','GITHUB_WORKSPACE':boot.CHECKOUT,
             'GITHUB_WORKFLOW_REF':profile.REPOSITORY+'/'+profile.WORKFLOW+'@'+profile.REF}
        return env,p

    def testEveryDispatchIdentityMutationRefuses(self):
        env,p=self.identity();accepted=boot.verify_dispatch(env,b'fixed',b'fixed',p)
        self.assertEqual(accepted['GITHUB_SHA'],'a'*40)
        for key in env:
            for value in ('','different'):
                changed=dict(env);changed[key]=value
                with self.subTest(key=key,value=value),self.assertRaises(boot.Refusal):boot.verify_dispatch(changed,b'fixed',b'fixed',p)
        with self.assertRaises(boot.Refusal):boot.verify_dispatch(env,b'new',b'fixed',p)

    def testModuleAndHostBytesAreAllBoundBeforeLoading(self):
        p=dict(vars(profile));sources={name+'.py':b'# '+name.encode() for name in boot.MODULES+('stage_b_bootstrap',)}
        p['MODULE_ROWS']=tuple((name,hashlib.sha256(raw).hexdigest()) for name,raw in sources.items())
        hosts={name:b'fixture '+name.encode() for name,_ in profile.HOST_ROWS}
        p['HOST_ROWS']=tuple((name,hashlib.sha256(raw).hexdigest()) for name,raw in hosts.items())
        p['HOST_ROWS_SHA256']=hashlib.sha256(json.dumps(list(p['HOST_ROWS']),sort_keys=True,separators=(',',':')).encode()).hexdigest()
        def read(path,limit):return sources[path.split('/')[-1]] if '/Tools/' in path else hosts[path.removeprefix(boot.RELATIVE+'/')]
        source,host=boot.admit_sources(p,read);self.assertEqual(len(source),len(boot.MODULES)+1);self.assertEqual(host,hosts)
        for bad in sources:
            saved=sources[bad];sources[bad]=saved+b'!'
            with self.assertRaises(boot.Refusal):boot.admit_sources(p,read)
            sources[bad]=saved
        p['MODULE_ROWS']+=p['MODULE_ROWS'][:1]
        with self.assertRaises(boot.Refusal):boot.admit_sources(p,read)

    def testPreloadedProjectModuleCannotBeAdopted(self):
        with patch.dict(boot.sys.modules,{'stage_b_profile':object()}):
            with self.assertRaises(boot.Refusal):boot.load_modules({}, {})


class SourceReadTests(unittest.TestCase):
    def setUp(self):
        import stat
        from copy import copy
        from test_stage_b_receipt import metadata
        self.copy=copy;self.raw=b'fixed source';self.value=metadata(55,size=len(self.raw));self.position=0
        self.next=100;self.closed=[];self.flags=[];self.stack=ExitStack();self.addCleanup(self.stack.close)
        def opened(name,flags,**kw):
            self.flags.append(flags);self.next+=1;return self.next
        def read(fd,size):
            data=self.raw[self.position:self.position+size];self.position+=len(data);return data
        self.open=self.stack.enter_context(patch.object(boot.os,'open',side_effect=opened))
        self.read=self.stack.enter_context(patch.object(boot.os,'read',side_effect=read))
        self.stack.enter_context(patch.object(boot.os,'getuid',return_value=501))
        self.stack.enter_context(patch.object(boot.os,'fstat',side_effect=lambda fd:copy(self.value)))
        self.named=self.stack.enter_context(patch.object(boot.os,'stat',side_effect=lambda *a,**kw:copy(self.value)))
        self.close=self.stack.enter_context(patch.object(boot.os,'close',side_effect=lambda fd:self.closed.append(fd)))

    def testSourceBytesUseFiniteNoFollowDescriptorsThenCloseAll(self):
        self.assertEqual(boot.read_source('native/fixed.py',100),self.raw)
        self.assertTrue(all(flags & boot.os.O_NOFOLLOW for flags in self.flags))
        self.assertTrue(self.flags[-1] & boot.os.O_NONBLOCK)
        self.assertEqual(len(self.closed),self.open.call_count);self.assertEqual(len(self.closed),len(set(self.closed)))

    def testNonregularAndOversizeRejectBeforeRead(self):
        import stat
        for mode,size in ((stat.S_IFIFO|0o600,2),(stat.S_IFLNK|0o600,2),(stat.S_IFREG|0o600,101)):
            self.value.st_mode=mode;self.value.st_size=size
            with self.assertRaises(boot.Refusal):boot.read_source('native/fixed.py',100)
        self.read.assert_not_called()

    def testSourceShortReadAndNamedReplacementReject(self):
        with patch.object(boot.os,'read',return_value=b''):
            with self.assertRaises(boot.Refusal):boot.read_source('native/fixed.py',100)
        other=self.copy(self.value);other.st_ino+=1;self.named.side_effect=lambda *a,**kw:other
        with self.assertRaises(boot.Refusal):boot.read_source('native/fixed.py',100)

    def testIntermediateFailureAndAmbiguousCloseStillRetireEachOnce(self):
        self.open.side_effect=[10,11,OSError('parent unavailable')]
        self.close.side_effect=lambda fd: (_ for _ in ()).throw(OSError('close ambiguous')) if fd==11 else self.closed.append(fd)
        with self.assertRaisesRegex(OSError,'parent unavailable'):boot.read_source('native/fixed.py',100)
        self.assertEqual([c.args[0] for c in self.close.call_args_list],[11,10])

    def testTraversalOrOtherSystemPathRefusesBeforeOpen(self):
        for path in ('../outside','native/../outside','/outside','native//file'):
            with self.assertRaises(boot.Refusal):boot.read_source(path,100)
        with self.assertRaises(boot.Refusal):boot.read_source('Users/runner/private',4096,_system=True)
        self.open.assert_not_called()

    def testSystemVersionMetadataHasExactFixedPathAndSupportedRange(self):
        import plistlib
        for version,allowed in (('15.3',True),('15.7.9',True),('15.2',False),('14.7',False),('26.0',False)):
            data=plistlib.dumps({'ProductVersion':version,'ProductBuildVersion':'synthetic'})
            with patch.object(boot,'read_source',return_value=data) as read,patch.object(boot.os,'uname',return_value=SimpleNamespace(machine='arm64')):
                if allowed:self.assertEqual(boot.system_version()['version'],version)
                else:
                    with self.assertRaises(boot.Refusal):boot.system_version()
                read.assert_called_once_with('System/Library/CoreServices/SystemVersion.plist',4096,_system=True)


class DriverTests(unittest.TestCase):
    def testDisabledDriverDoesNoOutputOrCreation(self):
        with patch.object(profile,'BUILD_ONLY_ENABLED',False), \
             patch.object(driver.sr.Report,'create') as report,patch.object(driver.ec.Experiment,'prepare') as prepare:
            with self.assertRaisesRegex(pc.Refusal,'^build-only profile disabled$'):
                driver.run({}, {},started_at=0)
            report.assert_not_called();prepare.assert_not_called()

    def run_model(self, failures=()):
        subject,inspection,_=model();order=[];subject.generated_rows=();subject.trace=[]
        subject.inspect_b=Mock(return_value=inspection);subject.close_outcomes={'fixture':'closed','workspace':'closed'}
        subject.close=Mock(side_effect=lambda:order.append('source-close'))
        report=Mock();report.add.side_effect=lambda *a:order.append('add:'+a[0])
        def finalise(raw):
            order.append('report-finalise');payload=json.loads(raw)
            return SimpleNamespace(path='/private/tmp/disk-selection-report-abc',manifest_sha256='c'*64,manifest_bytes=32,
                root_device=1,root_inode=2,outcome=payload['outcome'])
        report.finalise.side_effect=finalise
        admission=Mock();identity={'GITHUB_REPOSITORY':profile.REPOSITORY,'GITHUB_REF':profile.REF,'GITHUB_EVENT_NAME':'create','CREATED_REF_TYPE':'branch','CREATED_REF':profile.REF.removeprefix('refs/heads/'),
            'GITHUB_RUN_ATTEMPT':'1','GITHUB_RUN_ID':'123','GITHUB_SHA':'a'*40}
        capture=SimpleNamespace(captures=(),failures=())
        with ExitStack() as stack:
            stack.enter_context(patch.object(profile,'BUILD_ONLY_ENABLED',True))
            stack.enter_context(patch.object(driver.ec,'_source_files',return_value=profile.HOST_ROWS))
            stack.enter_context(patch.object(driver.ba,'_issue',return_value=admission))
            stack.enter_context(patch.object(driver.sr.Report,'create',return_value=report))
            stack.enter_context(patch.object(driver.ec.Experiment,'prepare',return_value=subject))
            stack.enter_context(patch.object(driver.sr,'capture_configurations',return_value=capture))
            stack.enter_context(patch.object(driver.ec,'_verify_inputs',side_effect=lambda *a,**kw:{} if kw.get('retain') else None))
            stack.enter_context(patch.object(driver.time,'monotonic',return_value=1))
            subject.fixture.verify.return_value='verified';subject.workspace.inventory.return_value=()
            if 'build' in failures:subject.inspect_b.side_effect=pc.Refusal('first build')
            if 'export' in failures:report.add.side_effect=OSError('write failure')
            if 'close' in failures:subject.close.side_effect=OSError('close failure')
            if 'finalise' in failures:report.finalise.side_effect=OSError('manifest failure')
            stdout=StringIO()
            with redirect_stdout(stdout):code=driver.run(identity,{},started_at=0)
        return code,json.loads(stdout.getvalue().removeprefix('OWNED_BUILD_TERMINAL ')),subject,report,order

    def testReportFinalisationFollowsActualSourceClose(self):
        code,record,subject,report,order=self.run_model()
        self.assertEqual(code,0);self.assertEqual(record['outcome'],'candidate_pass')
        self.assertLess(order.index('source-close'),order.index('report-finalise'));subject.close.assert_called_once()
        self.assertEqual(record['root_inode'],2)

    def testCombinedBuildExportCloseFailureNeverSkipsRetirement(self):
        code,record,subject,report,_=self.run_model(('build','export','close','finalise'))
        self.assertEqual(code,2);self.assertEqual(record['outcome'],'failed')
        self.assertEqual(record['failures'][0]['phase'],'prepare-or-build')
        subject.close.assert_called_once();report.finalise.assert_called_once();report.abort.assert_called_once()
        self.assertGreater(subject.workspace.inventory.call_count,1)

    def testEverySingleFailurePreventsCandidatePass(self):
        for failure in ('build','export','close','finalise'):
            with self.subTest(failure=failure):
                code,record,subject,_,_=self.run_model((failure,))
                self.assertEqual(code,2);self.assertEqual(record['outcome'],'failed');subject.close.assert_called_once()

    def testJSONBoundsAndNonfiniteCannotBeExported(self):
        with self.assertRaises(pc.Refusal):driver.encode({'x':'a'*100},20)
        with self.assertRaises(ValueError):driver.encode(float('nan'))


if __name__=='__main__':unittest.main()
