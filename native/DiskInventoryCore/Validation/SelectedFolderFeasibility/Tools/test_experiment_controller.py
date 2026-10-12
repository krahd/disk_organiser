"""Controller/record models only. All process/filesystem/capability ops mocked."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import hashlib
import json
import unittest

import bounded_process as bp
import experiment_controller as ec
import native_observations as no
import owned_build_observation as ob
import probe_contract as pc
import xctestrun_binding as xb
import runner_expectations as rx
from test_native_observations import tool as observed_tool, ROOT, CASE
from test_owned_build_observation import observed_example

COMMIT='a'*40
CAPTURES=('100-selected-read-retired','101-panel-cancelled','102-active-cancelled','103-retry-retired')


def model():
    fixture=json.loads((Path(__file__).parent/'fixture-claim.example.json').read_bytes())
    claim=ec._json(fixture)
    owner=Mock(); owner.claim=claim; owner.verify.return_value=ec._sha(claim)
    workspace=Mock(); workspace.path=ROOT.removesuffix('/Products'); workspace.products_path=ROOT
    subject=ec.Experiment(ec._CONTROLLER_KEY,workspace,owner,COMMIT,(),(),())
    observations=no.collect(observed_tool,ROOT,CASE)
    context=subject._context(observations,rx.DERIVED_NAME)
    original=observed_example()
    binding=rx.derive('Owned.xctestrun',original,subject._expectations(observations))
    raw=binding.derived.raw
    workspace.read_configuration.side_effect=lambda name, *, check=None:original if name=='Owned.xctestrun' else raw
    rows=[{'path':p,'kind':'directory'} for p in no.PRODUCTS]
    rows += [{'path':p,'kind':'file','size':1,'sha256':'a'*64} for p in no.EXECUTABLES]
    rows.append({'path':no.PRODUCTS[0]+'/Contents/Resources/fixture.json','kind':'file','size':len(claim),'sha256':ec._sha(claim)})
    frozen=ob.FrozenBuild(raw,xb.parse(raw),tuple(ec._json(x).decode() for x in rows),no.PRODUCTS,context)
    inspection=ec.Inspection(frozen,observations,ec._sha(claim),COMMIT,(),(),rx.DERIVED_NAME,context,(),binding)
    subject.inspection=inspection; subject.state='inspected'
    return subject,inspection,fixture


def records(inspection,fixture):
    records=[]; host=inspection.observations.signatures[0]
    for index,method in enumerate(xb.METHODS):
        records.append((b'OWNED_SELECTION_PROCESS ',{'method':method,'sourceCommit':COMMIT,'runID':fixture['runID'],
                        'caseID':fixture['caseID'],'runnerPID':200,'hostPID':101+index}))
        records.append((b'OWNED_SELECTION_CASE ',{'method':method,'sourceCommit':COMMIT,'runID':fixture['runID'],'caseID':fixture['caseID']}))
    for index,(method,outcome,capture,pid) in enumerate([(xb.METHODS[0],'passed',CAPTURES[0],101),
              (xb.METHODS[1],'panel-cancelled',CAPTURES[1],102),(xb.METHODS[2],'read-cancelled',CAPTURES[2],103),
              (xb.METHODS[2],'passed',CAPTURES[3],103)]):
        controls=[] if outcome=='panel-cancelled' else [{'operation':x,'errno':13} for x in
                      ('sibling-read-open','parent-entry-read','selected-write-open','selected-create-exclusive')]
        receipt={'schemaVersion':1,'sourceCommit':COMMIT,'runID':fixture['runID'],'caseID':fixture['caseID'],'pid':pid,
                 'observedIdentifier':host.identifier,'observedExecutable':host.executable,'observedCDHash':host.cdhash,
                 'runningValidityChecked':True,'error':'','outcome':outcome,'borrowedWorkerRetired':True,
                 'scopeRetired':True,'panelRetired':True,'beforeOperation':'selected-content-open','beforeErrno':13,
                 'afterOperation':'selected-content-open','afterErrno':13,'activeControls':controls,'positiveReadReachedControls':len(controls)==4}
        records.append((b'OWNED_SELECTION_UI_RECEIPT ',{'method':method,'capture':capture,'captureSHA256':'d'*64,
                        'captureBytes':123,'pixelWidth':640,'pixelHeight':420,'receipt':receipt}))
    return records


def output(inspection,rows):
    context=json.loads(inspection.context)
    return bp.ProcessResult((context['executable'],*context['arguments']),b'\n'.join(k+ec._json(v) for k,v in rows),b'',0,True,False,'',True)


def capture_rows():
    return tuple(ec._json(x).decode() for x in [{'path':'.','kind':'directory'}]+[
        {'path':name+'.png','kind':'file','size':123,'sha256':'d'*64} for name in CAPTURES])


class ExecutionRecordTests(unittest.TestCase):
    def setUp(self): self.subject,self.inspection,self.fixture=model(); self.rows=records(self.inspection,self.fixture)
    def verify(self,rows=None,result=None):
        return ec.verify_execution_output(result or output(self.inspection,self.rows if rows is None else rows),self.inspection,self.subject.fixture.claim)

    def testCompleteThreeMethodsFourCapturesAndBoundHostIdentities(self):
        methods,captures,pids=self.verify()
        self.assertEqual(methods,tuple(sorted(xb.METHODS)));self.assertEqual(captures,tuple(sorted(CAPTURES)))
        self.assertEqual(pids,(101,102,103,200))
        ec.verify_capture_inventory(capture_rows(),output(self.inspection,self.rows).stdout)

    def testForeignSourceFixtureMethodAndDuplicateCasesRefuse(self):
        for key,value in [('sourceCommit','b'*40),('caseID','33333333-3333-4333-8333-333333333333'),('method','Other/test')]:
            changed=deepcopy(self.rows); changed[1][1][key]=value
            with self.assertRaises(pc.Refusal):self.verify(changed)
        with self.assertRaises(pc.Refusal):self.verify(self.rows+[deepcopy(self.rows[1])])
        with self.assertRaises(pc.Refusal):self.verify(self.rows[1:])

    def testRuntimeCDHashMustMatchRetainedBObservation(self):
        for field,value in [('observedCDHash','b'*40),('observedExecutable','/other'),('observedIdentifier','other'),('runningValidityChecked',1)]:
            changed=deepcopy(self.rows); changed[-1][1]['receipt'][field]=value
            with self.assertRaises(pc.Refusal):self.verify(changed)

    def testHostPIDCannotBeRunnerOrAnotherMethod(self):
        for pid in (200,101,True,103.0):
            changed=deepcopy(self.rows);changed[-1][1]['receipt']['pid']=pid
            with self.assertRaises(pc.Refusal):self.verify(changed)

    def testACLSetupAndWrongErrnoNeverSatisfySelectedDenial(self):
        for field,value in [('beforeOperation','fstatx_np'),('afterOperation','filesec_query'),('beforeErrno',2),('afterErrno',True)]:
            changed=deepcopy(self.rows);changed[-1][1]['receipt'][field]=value
            with self.assertRaises(pc.Refusal):self.verify(changed)

    def testActiveControlWrongFamilyAndMissingPositiveReadRefuse(self):
        for mutation in (lambda x:x['activeControls'][0].update(operation='selected-write-open'),
                         lambda x:x.update(positiveReadReachedControls=False),lambda x:x.update(activeControls=[]),
                         lambda x:x.update(scopeRetired=False),lambda x:x.update(error='failure')):
            changed=deepcopy(self.rows);mutation(changed[-1][1]['receipt'])
            with self.assertRaises(pc.Refusal):self.verify(changed)

    def testUnreapedFailedCancelledOrDifferentToolOutputRefuses(self):
        result=output(self.inspection,self.rows)
        for changed in (replace(result,returncode=1),replace(result,direct_child_reaped=False),replace(result,cancelled=True),
                        replace(result,arguments=(no.XCODE,'build')),replace(result,reason='overflow')):
            with self.assertRaises(pc.Refusal):self.verify(result=changed)

    def testRawOutputBudgetAndMalformedRecordRefuse(self):
        with self.assertRaises(pc.Refusal):self.verify(result=replace(output(self.inspection,self.rows),stdout=b'x'*(bp.MAX_OUTPUT+1)))
        with self.assertRaises(pc.Refusal):self.verify(result=replace(output(self.inspection,self.rows),stdout=b'OWNED_SELECTION_CASE {bad'))

    def testMissingChangedExtraAndDuplicateOriginalsRefuse(self):
        raw=output(self.inspection,self.rows).stdout; rows=capture_rows()
        for changed in (rows[:-1],rows+('{"path":"extra.png","kind":"file"}',),
                        tuple(x.replace('d'*64,'e'*64) for x in rows)):
            with self.assertRaises(pc.Refusal):ec.verify_capture_inventory(changed,raw)
        for field,value in [('captureBytes',True),('pixelWidth',0),('captureSHA256','invalid')]:
            changed=deepcopy(self.rows);changed[-1][1][field]=value
            with self.assertRaises(pc.Refusal):ec.verify_capture_inventory(rows,output(self.inspection,changed).stdout)


class ControllerOwnerTests(unittest.TestCase):
    def setUp(self): self.subject,self.inspection,self.fixture=model()

    def testClosedBAndCGatesPrecedeAnyOperation(self):
        with patch.object(ec.ob.OwnedBuild,'create') as create,patch.object(ec.fi,'create_owned_fixture') as fixture:
            with self.assertRaisesRegex(pc.Refusal,'Stage B closed'):ec.Experiment.prepare(COMMIT,{})
            create.assert_not_called();fixture.assert_not_called()
        with patch.object(self.subject,'_observe') as observe:
            with self.assertRaisesRegex(pc.Refusal,'Stage C closed'):self.subject.run_c(self.inspection)
            observe.assert_not_called();self.assertEqual(self.subject.state,'inspected')

    def testPathOrImportedInspectionCannotReacquireOwner(self):
        with self.assertRaises(pc.Refusal):ec.Experiment(object(),None,None,COMMIT,(),(),())
        with patch.object(ec,'_stage_c_approved',return_value=True),patch.object(self.subject,'_observe') as observe:
            with self.assertRaisesRegex(pc.Refusal,'retained exact'):self.subject.run_c(replace(self.inspection))
            observe.assert_not_called()

    def testPrepareRequiresPinnedSourceBeforeCreatingAnything(self):
        files={name:b'synthetic' for name in ['Probe.xcodeproj/project.pbxproj','Probe.xcodeproj/xcshareddata/xcschemes/OwnedFolderProbe.xcscheme',
               'Host/main.swift','Host/host.entitlements.inert.plist','Generated/ProbeSeal.swift','Generated/fixture.json',
               'Generated/ProbeBuild.xcconfig','UITests/SelectionProbeUITests.swift']}
        with patch.object(ec,'_stage_b_approved',return_value=True),patch.object(ec.ob.OwnedBuild,'create') as create:
            with self.assertRaisesRegex(pc.Refusal,'reviewed source'):ec.Experiment.prepare(COMMIT,files)
            create.assert_not_called()

    def testFailedPreparationRetiresBothCapabilitiesWithoutDeletion(self):
        files={name:b'synthetic' for name in ['Probe.xcodeproj/project.pbxproj','Probe.xcodeproj/xcshareddata/xcschemes/OwnedFolderProbe.xcscheme',
               'Host/main.swift','Host/host.entitlements.inert.plist','Generated/ProbeSeal.swift','Generated/fixture.json',
               'Generated/ProbeBuild.xcconfig','UITests/SelectionProbeUITests.swift']}
        workspace=Mock();workspace.products_path=ROOT;workspace.create_captures_directory.return_value={'device':1,'inode':9}
        owner=Mock();owner.claim=self.subject.fixture.claim
        with patch.object(ec,'_stage_b_approved',return_value=True),patch.object(ec,'REVIEWED_SOURCE_COMMIT',COMMIT), \
             patch.object(ec,'REVIEWED_SOURCE_MANIFEST_SHA256',ec._sha(ec._json(list(ec._source_files(files))))), \
             patch.object(ec.ob.OwnedBuild,'create',return_value=workspace),patch.object(ec.fi,'create_owned_fixture',return_value=owner), \
             patch.object(ec.fi,'render_claimed_inputs',return_value={}),patch.object(ec,'_write_inputs',side_effect=pc.Refusal('synthetic write')):
            with self.assertRaisesRegex(pc.Refusal,'synthetic write'):ec.Experiment.prepare(COMMIT,files)
        owner.close.assert_called_once();workspace.close.assert_called_once()

    def testChangedPreflightCannotSpawnAndConsumesAttempt(self):
        changed=replace(self.inspection,fixture_digest='d'*64)
        with patch.object(ec,'_stage_c_approved',return_value=True),patch.object(self.subject,'_observe',return_value=changed), \
             patch.object(self.subject,'_tool') as tool,patch.object(ec,'_verify_inputs'):
            with self.assertRaisesRegex(pc.Refusal,'changed before runtime'):self.subject.run_c(self.inspection)
            tool.assert_not_called();self.assertEqual(self.subject.state,'failed')
            with self.assertRaisesRegex(pc.Refusal,'retained exact'):self.subject.run_c(self.inspection)

    def testCompleteMockRuntimeRequiresPostObservationResultsAndRetirement(self):
        result=output(self.inspection,records(self.inspection,self.fixture))
        self.subject.workspace.inventory.side_effect=lambda **kw:capture_rows() if kw.get('captures') else ('{"path":".","kind":"directory"}','{"path":"Data/blob","kind":"file"}')
        with patch.object(ec,'_stage_c_approved',return_value=True),patch.object(self.subject,'_observe',return_value=self.inspection) as observe, \
             patch.object(self.subject,'_tool',return_value=result) as tool,patch.object(ec.bp,'prove_retired',return_value=(101,102,103,200)) as retire:
            receipt=self.subject.run_c(self.inspection)
        self.assertEqual(self.subject.state,'retired');self.assertEqual(observe.call_count,2)
        self.assertEqual(receipt.original_capture_inventory,capture_rows());self.assertEqual(len(receipt.methods),3)
        self.assertIn('test-without-building',tool.call_args.args[0]);retire.assert_called_once_with((101,102,103,200))

    def testAliveProcessPostMutationAndMissingOriginalsCannotPass(self):
        for failure in ('alive','changed','images'):
            subject,inspection,fixture=model(); result=output(inspection,records(inspection,fixture))
            subject.workspace.inventory.side_effect=lambda **kw:() if kw.get('captures') else ('{"path":"Data/blob","kind":"file"}',)
            observations=[inspection,replace(inspection,fixture_digest='e'*64)] if failure=='changed' else [inspection,inspection]
            with patch.object(ec,'_stage_c_approved',return_value=True),patch.object(subject,'_observe',side_effect=observations), \
                 patch.object(subject,'_tool',return_value=result),patch.object(ec.bp,'prove_retired',side_effect=pc.Refusal('still alive') if failure=='alive' else None,return_value=(101,102,103,200)),patch.object(ec,'_verify_inputs'):
                with self.assertRaises(pc.Refusal):subject.run_c(inspection)
                self.assertEqual(subject.state,'failed')

    def testPartialRuntimeFailureRetainsOutputAndChecksKnownProcesses(self):
        partial=replace(output(self.inspection,records(self.inspection,self.fixture)),returncode=-15,reason='tool-deadline')
        with patch.object(ec,'_stage_c_approved',return_value=True),patch.object(self.subject,'_observe',return_value=self.inspection), \
             patch.object(self.subject,'_tool',side_effect=bp.ProcessFailure(partial)),patch.object(ec.bp,'prove_retired',return_value=(101,102,103,200)) as retire,patch.object(ec,'_verify_inputs'):
            with self.assertRaises(bp.ProcessFailure):self.subject.run_c(self.inspection)
            retire.assert_called_once_with((101,102,103,200));self.assertEqual(self.subject.state,'failed')

    def testCloseDoesNotSkipSecondOwnerWhenFirstCloseFails(self):
        self.subject.fixture.close.side_effect=pc.Refusal('ambiguous')
        with self.assertRaisesRegex(pc.Refusal,'retirement unproved'):self.subject.close()
        self.subject.workspace.close.assert_called_once();self.assertEqual(self.subject.state,'closed')

    def testObserveRequiresActualExecutableAndResourceRows(self):
        for remove in (no.EXECUTABLES[0],no.PRODUCTS[0]+'/Contents/Resources/fixture.json'):
            frozen=replace(self.inspection.freeze,inventory=tuple(x for x in self.inspection.freeze.inventory if json.loads(x)['path']!=remove))
            with patch.object(ec,'_verify_inputs'),patch.object(ec.no,'collect',return_value=self.inspection.observations),patch.object(ec.ob,'freeze',return_value=frozen):
                with self.assertRaises(pc.Refusal):self.subject._observe(rx.DERIVED_NAME,self.inspection.runner_binding)
        with patch.object(ec,'_verify_inputs'),patch.object(ec.no,'collect',return_value=self.inspection.observations),patch.object(ec.ob,'freeze',return_value=self.inspection.freeze):
            observed=self.subject._observe(rx.DERIVED_NAME,self.inspection.runner_binding)
        self.assertEqual(observed,self.inspection)

    def testBuildInspectionRunsOnlyFixedBuildAndOwnedSigningCommands(self):
        self.subject.state='prepared'
        def recorded(args,**kwargs):
            value=bp.ProcessResult(args,b'synthetic build observation',b'',0,True,False,'',True)
            self.subject.trace.append(value);return value
        with patch.object(ec,'_stage_b_approved',return_value=True),patch.object(ec,'_verify_inputs'), \
             patch.object(self.subject,'_configuration_name',return_value='Owned.xctestrun'), \
             patch.object(self.subject,'_prepare_runner_binding',return_value=self.inspection.runner_binding), \
             patch.object(self.subject,'_observe',return_value=self.inspection),patch.object(self.subject,'_tool',side_effect=recorded) as tool:
            inspection=self.subject.inspect_b()
        calls=[x.args[0] for x in tool.call_args_list]
        self.assertEqual(len(calls),4);self.assertEqual(calls[0][:2],(no.XCODE,'build-for-testing'))
        self.assertIn('CODE_SIGNING_ALLOWED=NO',calls[0])
        self.assertFalse(any('test-without-building' in x for x in calls))
        self.assertEqual([x[-1] for x in calls[1:]],[ROOT+'/'+no.PRODUCTS[i] for i in (2,1,0)])
        self.assertTrue(all('--entitlements' not in x for x in calls[1:3]));self.assertIn('--entitlements',calls[3])
        self.assertEqual(len(inspection.preparation_log_digests),4);self.assertEqual(self.subject.state,'inspected')

    def testBuildFailureDoesNotProceedToSigningOrRuntime(self):
        self.subject.state='prepared'
        failure=bp.ProcessFailure(bp.ProcessResult((no.XCODE,'build-for-testing'),b'compiler failure',b'',65,True,False,'tool-exit',True))
        with patch.object(ec,'_stage_b_approved',return_value=True),patch.object(ec,'_verify_inputs'), \
             patch.object(self.subject,'_tool',side_effect=failure) as tool:
            with self.assertRaises(bp.ProcessFailure):self.subject.inspect_b()
        self.assertEqual(tool.call_count,1);self.assertEqual(self.subject.state,'failed');self.assertFalse(self.subject._active_cancel())

    def testActiveCloseAndForeignThreadRefuseWithoutRetiringRoots(self):
        for state in ('preparing','running'):
            self.subject.state=state
            with self.assertRaisesRegex(pc.Refusal,'borrowed'):self.subject.close()
            self.subject.fixture.close.assert_not_called();self.subject.workspace.close.assert_not_called()
        self.subject.state='inspected'
        with patch.object(ec.threading,'get_ident',return_value=self.subject._owner_thread+1):
            with self.assertRaisesRegex(pc.Refusal,'owner thread'):self.subject.close()
            with self.assertRaisesRegex(pc.Refusal,'owner thread'):self.subject.run_c(self.inspection)

    def testCancellationSignalAppliesToPreflightObservationTools(self):
        self.subject._active_cancel=lambda:True
        with patch.object(ec.bp,'run') as run:
            self.subject._tool(('/usr/bin/codesign','--verify',ROOT),timeout=1)
            self.assertTrue(run.call_args.kwargs['cancelled']())

if __name__ == '__main__':unittest.main()
