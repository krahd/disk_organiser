"""Whole admitted-controller models. All tool/filesystem operations are mocked."""
from dataclasses import replace
from unittest.mock import patch
import unittest

import experiment_controller as ec
import native_observations as no
import probe_contract as pc
import stage_b_admission as ba
import stage_b_profile as profile
from test_experiment_controller import model
from test_native_observations import tool as observed_tool

IDENTITY = (1,2,0o100755,0,0,1000,3,4)


def attach(subject):
    admission=ba._issue(0,lambda:1)
    admission.consume(profile.HOST_SOURCE_COMMIT,profile.HOST_ROWS)
    admission.attach(subject);subject._build_admission=admission
    return admission


def good_tool(args,**kw):
    if 'build-for-testing' in args or '--force' in args:
        return ec.bp.ProcessResult(args,b'synthetic build/sign',b'',0,True,False,'',True)
    return observed_tool(args,**kw)


class HostDependencyControllerTests(unittest.TestCase):
    def testEveryInspectorFailureStopsBeforeBindingAndRetainsFirstFailure(self):
        cases=('absent','precall-change','postcall-change','exit','timeout','overflow','child','group','cancel','stderr','grammar')
        for case in cases:
            with self.subTest(case=case):
                subject,_,_=model();subject.state='prepared';subject.inspection=None
                subject.workspace.inventory.return_value=('partial-owned-row',)
                changed=IDENTITY[:-1]+(5,)
                states=[FileNotFoundError('fixed inspector absent')] if case=='absent' else [IDENTITY,changed] if case=='precall-change' else [IDENTITY,IDENTITY,changed] if case=='postcall-change' else [IDENTITY]*3
                observed_failure=[]
                def tool(args,**kw):
                    value=good_tool(args,**kw)
                    if args[0]==no.OTOOL:
                        mutation={'exit':dict(returncode=1,reason='tool-exit'),
                                  'timeout':dict(returncode=-15,reason='tool-deadline'),
                                  'overflow':dict(reason='output-limit'),
                                  'child':dict(direct_child_reaped=False,reason='retirement-unproved'),
                                  'group':dict(owned_group_retired=False,reason='retirement-unproved'),
                                  'cancel':dict(cancelled=True,reason='cancelled'),
                                  'stderr':dict(stderr=b'diagnostic'),
                                  'grammar':dict(stdout=value.stdout[:-1])}.get(case,{})
                        value=replace(value,**mutation)
                        if value.reason:
                            error=ec.bp.ProcessFailure(value);observed_failure.append(error);raise error
                    return value
                with patch.object(profile,'BUILD_ONLY_ENABLED',True),patch.object(ec,'_verify_inputs'), \
                     patch.object(no,'inspector_identity',side_effect=states),patch.object(ec.bp,'run',side_effect=tool) as run, \
                     patch.object(subject,'_prepare_runner_binding') as binding,patch.object(subject,'_observe') as observe:
                    admission=attach(subject)
                    with self.assertRaises((FileNotFoundError,pc.Refusal,ec.bp.ProcessFailure)) as caught:
                        subject.inspect_b()
                    expected=3 if case=='absent' else 7 if case=='precall-change' else 8
                    self.assertEqual(run.call_count,expected);self.assertEqual(admission.guard.count,expected)
                    binding.assert_not_called();observe.assert_not_called()
                    self.assertEqual(subject.state,'failed');self.assertIsNone(subject.inspection)
                    self.assertEqual(subject.failure,type(caught.exception).__name__)
                    if observed_failure:self.assertIs(caught.exception,observed_failure[0])
                    self.assertEqual(len(subject.failure_evidence['tool_results']),expected)
                    self.assertEqual(subject.failure_evidence['fixture'],'unchanged')
                    self.assertEqual(subject.failure_evidence['source'],'unchanged')
                    self.assertEqual(subject.failure_evidence['partial_products'],('partial-owned-row',))
                    self.assertEqual(sum(x.arguments[0]==no.OTOOL for x in subject.trace),int(expected==8))
                    with self.assertRaises(pc.Refusal):subject.inspect_b()
                    self.assertEqual(run.call_count,expected)
                    subject.close()
                    subject.fixture.close.assert_called_once();subject.workspace.close.assert_called_once()
                    self.assertEqual(admission.state,'retired')

    def testSuccessfulSignaturesAndInspectionCannotMaskUnexpectedMacOSLeaf(self):
        for name in ('OwnedFolderProbe.debug.dylib','__preview.dylib','Other'):
            subject,inspection,_=model();subject.state='prepared';subject.inspection=None
            extra=ec._json(dict(path=no.PRODUCTS[0]+'/Contents/MacOS/'+name,kind='file',size=100,sha256='c'*64)).decode()
            frozen=replace(inspection.freeze,inventory=inspection.freeze.inventory+(extra,))
            subject.workspace.inventory.return_value=('partial-owned-row',)
            with patch.object(profile,'BUILD_ONLY_ENABLED',True),patch.object(ec,'_verify_inputs'), \
                 patch.object(ec,'_write_bound_configuration'),patch.object(no,'inspector_identity',return_value=IDENTITY), \
                 patch.object(ec.ob,'freeze',return_value=frozen),patch.object(subject,'_configuration_name',return_value='Owned.xctestrun'), \
                 patch.object(ec.bp,'run',side_effect=good_tool) as run:
                admission=attach(subject)
                with self.assertRaisesRegex(pc.Refusal,'unexpected host executable layout'):subject.inspect_b()
                self.assertEqual(run.call_count,32);self.assertEqual(admission.guard.count,32)
                self.assertEqual(subject.state,'failed');self.assertIsNone(subject.inspection)
                self.assertEqual(sum(x.arguments[0]==no.OTOOL for x in subject.trace),1)
                self.assertEqual(subject.failure_evidence['tool_results'][7].stdout,
                                 observed_tool(subject.trace[7].arguments).stdout)
                with self.assertRaises(pc.Refusal):subject.run_c(inspection)
                self.assertEqual(run.call_count,32)
                subject.close();self.assertEqual(admission.state,'retired')


if __name__=='__main__':unittest.main()
