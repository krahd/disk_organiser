"""Mocked B failure/write ownership and whole-inspection mutation regressions."""
from dataclasses import fields, is_dataclass, replace
from types import SimpleNamespace
from unittest.mock import Mock, patch
import os
import unittest

import bounded_process as bp
import experiment_controller as ec
import native_observations as no
import probe_contract as pc
import runner_expectations as rx
from test_experiment_controller import model, records, output, capture_rows


def changed_leaves(value, path=()):
    if is_dataclass(value):
        for field in fields(value):
            for subpath,child in changed_leaves(getattr(value,field.name),path+(field.name,)):
                yield subpath,replace(value,**{field.name:child})
    elif type(value) is tuple and value:
        for index,item in enumerate(value):
            for subpath,child in changed_leaves(item,path+(str(index),)):
                yield subpath,value[:index]+(child,)+value[index+1:]
    else:
        changed = value+b'changed' if type(value) is bytes else value+'changed' if type(value) is str else not value if type(value) is bool else value+1 if type(value) is int else ('changed',)
        yield path,changed


class InspectionFingerprintTests(unittest.TestCase):
    def testEveryRetainedLeafParticipatesInVersionedFingerprint(self):
        _,inspection,_=model();digest=ec.inspection_digest(inspection)
        self.assertEqual(digest,ec.inspection_digest(replace(inspection)))
        mutations=list(changed_leaves(inspection));self.assertGreater(len(mutations),60)
        seen=set()
        for path,changed in mutations:
            with self.subTest(path=path):self.assertNotEqual(digest,ec.inspection_digest(changed))
            seen.add(path[0])
        self.assertEqual(seen,{x.name for x in fields(inspection)})

    def testTypesAndBoundariesCannotCollide(self):
        samples=[b'a','a',('a',),('ab','c'),('a','bc'),True,1,()]
        self.assertEqual(len({ec._json(ec._canonical(x)) for x in samples}),len(samples))
        with self.assertRaises(pc.Refusal):ec.inspection_digest({})
        with self.assertRaises(pc.Refusal):ec._canonical(object())

    def testRuntimeDigestDiffersWhenPreparationEvidenceDiffers(self):
        digests=[]
        for preparation in (('a'*64,),('b'*64,)):
            subject,inspection,fixture=model();inspection=replace(inspection,preparation_log_digests=preparation)
            subject.inspection=inspection
            subject.workspace.inventory.side_effect=lambda **kw:capture_rows() if kw.get('captures') else ('{"path":"blob","kind":"file"}',)
            with patch.object(ec,'_stage_c_approved',return_value=True),patch.object(subject,'_observe',return_value=inspection), \
                 patch.object(subject,'_tool',return_value=output(inspection,records(inspection,fixture))),patch.object(ec.bp,'prove_retired',return_value=(101,102,103,200)):
                receipt=subject.run_c(inspection)
            self.assertEqual(receipt.inspection_digest,ec.inspection_digest(inspection));digests.append(receipt.inspection_digest)
        self.assertNotEqual(*digests)


class PreparationFailureTests(unittest.TestCase):
    def testEveryBuildOrSigningFailureRetainsIndependentDisposition(self):
        for fail_at in range(4):
            subject,_,_=model();subject.state='prepared';subject.inspection=None;calls=[]
            subject.workspace.inventory.return_value=('partial-owned-row',)
            def run(args,**kw):
                index=len(calls);calls.append(args)
                result=bp.ProcessResult(args,b'partial bytes',b'diagnostic',65 if index==fail_at else 0,True,False,'tool-exit' if index==fail_at else '',True)
                if index==fail_at:raise bp.ProcessFailure(result)
                return result
            with patch.object(ec,'_stage_b_approved',return_value=True),patch.object(ec,'_verify_inputs') as source, \
                 patch.object(ec.bp,'run',side_effect=run),patch.object(subject,'_prepare_runner_binding') as binding:
                with self.assertRaises(bp.ProcessFailure) as failure:subject.inspect_b()
            self.assertEqual(len(calls),fail_at+1);binding.assert_not_called()
            self.assertEqual(subject.state,'failed');self.assertIsNone(subject.inspection)
            self.assertEqual(subject.failure_evidence['fixture'],'unchanged');self.assertEqual(subject.failure_evidence['source'],'unchanged')
            self.assertEqual(subject.failure_evidence['partial_products'],('partial-owned-row',))
            self.assertEqual(subject.failure_evidence['partial_captures'],('partial-owned-row',))
            self.assertIs(subject.failure_evidence['tool_results'][-1],failure.exception.result)
            self.assertEqual(subject.failure_evidence['tool_results'][-1].stdout,b'partial bytes')
            self.assertEqual(source.call_count,2)

    def testFailureOfOneEvidenceAttemptDoesNotSkipTheRest(self):
        subject,_,_=model();subject.state='prepared';subject.fixture.verify.side_effect=pc.Refusal('fixture changed')
        subject.workspace.inventory.side_effect=[FileNotFoundError('missing'),('captures retained',)]
        with patch.object(ec,'_stage_b_approved',return_value=True),patch.object(ec,'_verify_inputs',side_effect=pc.Refusal('source changed')) as source,patch.object(subject,'_tool') as tool:
            with self.assertRaisesRegex(pc.Refusal,'fixture changed'):subject.inspect_b()
        tool.assert_not_called();source.assert_called_once()
        self.assertEqual(subject.failure_evidence['fixture'],'unproved:Refusal')
        self.assertEqual(subject.failure_evidence['source'],'unproved:Refusal')
        self.assertEqual(subject.failure_evidence['partial_products'],'unproved:FileNotFoundError')
        self.assertEqual(subject.failure_evidence['partial_captures'],('captures retained',))
        self.assertEqual(subject.failure,'Refusal');self.assertEqual(subject.failure_evidence['tool_results'],())

    def testUnprovedProcessRetirementIsRetainedWithoutInventingCleanup(self):
        subject,_,_=model();subject.state='prepared'
        failed=bp.ProcessResult((no.XCODE,'build-for-testing'),b'partial',b'',-1,False,True,'retirement-unproved',False)
        with patch.object(ec,'_stage_b_approved',return_value=True),patch.object(ec,'_verify_inputs'),patch.object(ec.bp,'run',side_effect=bp.ProcessFailure(failed)):
            with self.assertRaises(bp.ProcessFailure):subject.inspect_b()
        self.assertIs(subject.failure_evidence['tool_results'][0],failed)
        self.assertFalse(subject.failure_evidence['tool_results'][0].direct_child_reaped)
        subject.fixture.close.assert_not_called();subject.workspace.close.assert_not_called()


class BoundConfigurationWriteTests(unittest.TestCase):
    def setUp(self):self.subject,self.inspection,_=model();self.binding=self.inspection.runner_binding
    def metadata(self,size):return SimpleNamespace(st_mode=0o100600,st_nlink=1,st_uid=501,st_size=size,st_dev=1,st_ino=42)

    def testExclusiveFixedLeafShortWritesAndReadbackPreserveOriginal(self):
        workspace=self.subject.workspace;workspace._products.return_value=7;written=bytearray();attempt=[0]
        def write(fd,data):
            attempt[0]+=1
            if attempt[0]==1:raise InterruptedError()
            count=min(17,len(data));written.extend(data[:count]);return count
        final=self.metadata(len(self.binding.derived.raw))
        with patch.object(ec.os,'open',return_value=8) as opened,patch.object(ec.os,'fstat',side_effect=[self.metadata(0),final]), \
             patch.object(ec.os,'stat',return_value=final),patch.object(ec.os,'getuid',return_value=501), \
             patch.object(ec.os,'write',side_effect=write),patch.object(ec.os,'fsync') as sync,patch.object(ec.os,'close') as close:
            ec._write_bound_configuration(workspace,self.binding)
        self.assertEqual(bytes(written),self.binding.derived.raw);self.assertEqual(opened.call_args.args[0],rx.DERIVED_NAME)
        flags=opened.call_args.args[1]
        self.assertTrue(flags & os.O_EXCL and flags & os.O_NOFOLLOW and flags & os.O_NONBLOCK)
        self.assertFalse(flags & os.O_TRUNC);sync.assert_called_once_with(8);close.assert_called_once_with(8)

    def testExistingDerivedLeafRefusesWithoutOverwriteOrRetry(self):
        with patch.object(ec.os,'open',side_effect=FileExistsError()) as opened,patch.object(ec.os,'write') as write,patch.object(ec.os,'close') as close:
            with self.assertRaises(FileExistsError):ec._write_bound_configuration(self.subject.workspace,self.binding)
        opened.assert_called_once();write.assert_not_called();close.assert_not_called()

    def testWriteFailureAndNamedReplacementStillRetireAcquiredDescriptor(self):
        for failure in ('write','replacement'):
            final=self.metadata(len(self.binding.derived.raw));named=self.metadata(len(self.binding.derived.raw));named.st_ino=99
            with patch.object(ec.os,'open',return_value=8),patch.object(ec.os,'fstat',side_effect=[self.metadata(0),final]), \
                 patch.object(ec.os,'getuid',return_value=501),patch.object(ec.os,'write',side_effect=BlockingIOError() if failure=='write' else lambda fd,data:len(data)), \
                 patch.object(ec.os,'fsync'),patch.object(ec.os,'stat',return_value=named),patch.object(ec.os,'close') as close:
                with self.assertRaises((BlockingIOError,pc.Refusal)):ec._write_bound_configuration(self.subject.workspace,self.binding)
            close.assert_called_once_with(8)

    def testOriginalChangeRefusesBeforeCreatingNewLeaf(self):
        self.subject.workspace.read_configuration.return_value=None
        self.subject.workspace.read_configuration.side_effect=lambda name:self.binding.original.raw+b' '
        with patch.object(ec.os,'open') as opened:
            with self.assertRaises(pc.Refusal):ec._write_bound_configuration(self.subject.workspace,self.binding)
        opened.assert_not_called()

    def testPrepareBindsActualObservationAndCRechecksWithoutWriting(self):
        with patch.object(ec.no,'collect',return_value=self.inspection.observations),patch.object(ec,'_write_bound_configuration') as write:
            binding=self.subject._prepare_runner_binding('Owned.xctestrun')
        self.assertEqual(binding,self.binding);write.assert_called_once_with(self.subject.workspace,binding)
        bad=replace(self.inspection.observations,signatures=(replace(self.inspection.observations.signatures[0],cdhash='b'*40),)+self.inspection.observations.signatures[1:])
        with patch.object(ec.no,'collect',return_value=bad),patch.object(ec,'_verify_inputs'),patch.object(ec.ob,'freeze',return_value=self.inspection.freeze),patch.object(ec,'_write_bound_configuration') as write:
            with self.assertRaises(pc.Refusal):self.subject._observe(rx.DERIVED_NAME,binding)
        write.assert_not_called()

if __name__=='__main__':unittest.main()
