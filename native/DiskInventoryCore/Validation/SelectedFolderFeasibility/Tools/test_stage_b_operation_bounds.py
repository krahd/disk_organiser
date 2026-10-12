"""Actual owner loops with mocked OS boundaries; no roots or processes created."""
from contextlib import ExitStack, contextmanager
import errno
import hashlib
import json
import stat
import unittest
from unittest.mock import Mock, patch

import experiment_controller as ec
import fixture_inputs as fi
import owned_build_observation as ob
import probe_contract as pc
import stage_b_admission as ba
import stage_b_profile as profile
from test_experiment_controller import model
from test_stage_b_receipt import Entries, metadata

ROOT = '/private/tmp/disk-selection-build-synthetic'
FIXTURE_ROOT = '/private/tmp/disk-selection-owned-synthetic'


def close_records(error):
    result = []
    while error is not None:
        result.extend(getattr(error, 'cleanup_failures', ()))
        error = getattr(error, 'original', None)
    return result


def first_error(error):
    while getattr(error, 'original', None) is not None:
        error = error.original
    return error


@contextmanager
def budget_at(limit):
    """Use the real admission/command clocks for both existing absolute caps."""
    clock = [1.0]
    subject = None
    with patch.object(profile, 'BUILD_ONLY_ENABLED', True):
        admission = ba._issue(0, lambda: clock[0])
        admission.consume(profile.HOST_SOURCE_COMMIT, profile.HOST_ROWS)
        if limit == 900:
            subject, _, _ = model()
            admission.attach(subject)
            subject._build_admission = admission
            admission.stop()
            check = subject._finalisation_check
        else:
            check = admission.work_check
        clock[0] = limit - 1.0
        try:
            yield clock, check
        finally:
            if subject is not None:
                subject.close()
            else:
                admission.retire()


class OperationBoundsTests(unittest.TestCase):
    def source_owner(self, stack):
        owner = ob.OwnedBuild(ob._KEY, ROOT, 5, (1, 5))
        owner._products_identity = (1, 10)
        root = metadata(5, stat.S_IFDIR | 0o700)
        product = metadata(10, stat.S_IFDIR | 0o700)
        leaf = metadata(12, size=1)
        stack.enter_context(patch.object(ob.os, 'getuid', return_value=501))
        stack.enter_context(patch.object(ob.os, 'fstat', side_effect=lambda fd: root if fd == 5 else product if fd == 10 else leaf))
        stack.enter_context(patch.object(ob.os, 'stat', side_effect=lambda name, **kw: root if name == ROOT else product if name == 'Products' else leaf))
        close = stack.enter_context(patch.object(ob.os, 'close'))
        return owner, close

    def testActualSourceWriteRetainsENOSPCAndEveryCloseEINTR(self):
        original = OSError(errno.ENOSPC, 'FIRST_WRITE_ENOSPC')
        with ExitStack() as stack:
            owner, close = self.source_owner(stack)
            stack.enter_context(patch.object(ec.os, 'mkdir'))
            opened = stack.enter_context(patch.object(ec.os, 'open', side_effect=[10, 11, 12]))
            stack.enter_context(patch.object(ec.os, 'write', side_effect=original))
            sync = stack.enter_context(patch.object(ec.os, 'fsync'))
            close.side_effect = lambda fd: (_ for _ in ()).throw(OSError(errno.EINTR, 'CLOSE_' + str(fd)))
            with self.assertRaises(ob.RetirementFailure) as caught:
                ec._write_inputs(owner, {'Host/main.swift': b'x'})
            self.assertIs(caught.exception.original, original)
            self.assertEqual([row['errno'] for row in caught.exception.cleanup_failures], [errno.EINTR] * 3)
            self.assertEqual([row['descriptor'] for row in caught.exception.cleanup_failures], [12, 11, 10])
            self.assertIn('FIRST_WRITE_ENOSPC', ''.join(caught.exception.failures))
            self.assertEqual([call.args[0] for call in close.call_args_list], [12, 11, 10])
            self.assertEqual(opened.call_count, 3); sync.assert_not_called()
            with self.assertRaises(ob.RetirementFailure): owner.close()
            owner.close()
            self.assertEqual([call.args[0] for call in close.call_args_list], [12, 11, 10, 5])

    def testActualFixtureCreationRetainsWriteAndFourCloseFailures(self):
        original = OSError(errno.ENOSPC, 'FIRST_FIXTURE_WRITE')
        with ExitStack() as stack:
            stack.enter_context(patch.object(fi.sys, 'platform', 'darwin'))
            root = stack.enter_context(patch.object(fi.tempfile, 'mkdtemp', return_value=FIXTURE_ROOT))
            stack.enter_context(patch.object(fi.os, 'mkdir'))
            stack.enter_context(patch.object(fi.os, 'open', side_effect=[10, 11, 12, 13]))
            stack.enter_context(patch.object(fi.os, 'fstat', return_value=metadata(10, stat.S_IFDIR | 0o700)))
            stack.enter_context(patch.object(fi.os, 'getuid', return_value=501))
            stack.enter_context(patch.object(fi.os, 'write', side_effect=original))
            sync = stack.enter_context(patch.object(fi.os, 'fsync'))
            read = stack.enter_context(patch.object(fi.os, 'pread'))
            close = stack.enter_context(patch.object(fi.os, 'close', side_effect=OSError(errno.EINTR, 'FIXTURE_CLOSE')))
            with self.assertRaises(ob.RetirementFailure) as caught: fi.create_owned_fixture()
            self.assertIs(caught.exception.original, original)
            self.assertEqual([row['descriptor'] for row in close_records(caught.exception)], [13, 12, 11, 10])
            self.assertEqual([call.args[0] for call in close.call_args_list], [13, 12, 11, 10])
            root.assert_called_once(); sync.assert_not_called(); read.assert_not_called()

    def fixture_creation_io(self, stack):
        records = {10: metadata(10, stat.S_IFDIR | 0o700),
                   11: metadata(11, stat.S_IFDIR | 0o700),
                   12: metadata(12, stat.S_IFDIR | 0o700),
                   13: metadata(13, size=32), 14: metadata(14, size=32)}
        records.update({20: records[10], 21: records[11], 22: records[13],
                        23: records[12], 24: records[14]})
        stack.enter_context(patch.object(fi.sys, 'platform', 'darwin'))
        stack.enter_context(patch.object(fi.tempfile, 'mkdtemp', return_value=FIXTURE_ROOT))
        stack.enter_context(patch.object(fi.uuid, 'uuid4', side_effect=[
            '11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222']))
        stack.enter_context(patch.object(fi.os, 'mkdir'))
        stack.enter_context(patch.object(fi.os, 'open', side_effect=[10, 11, 12, 13, 14, 20, 21, 22, 23, 24]))
        stack.enter_context(patch.object(fi.os, 'fstat', side_effect=records.__getitem__))
        def named(name, **kwargs):
            if name == 'must-remain-absent.bin': raise FileNotFoundError(errno.ENOENT, 'absent')
            return records[10]
        stack.enter_context(patch.object(fi.os, 'stat', side_effect=named))
        stack.enter_context(patch.object(fi.os, 'getuid', return_value=501))
        write = stack.enter_context(patch.object(fi.os, 'write', side_effect=lambda fd, data: len(data)))
        stack.enter_context(patch.object(fi.os, 'fsync'))
        stack.enter_context(patch.object(fi.os, 'pread', side_effect=lambda fd, count, offset: pc.SELECTED if fd == 13 else pc.SIBLING))
        read = stack.enter_context(patch.object(fi.os, 'read', side_effect=[pc.SELECTED, b'', pc.SIBLING, b'']))
        close = stack.enter_context(patch.object(fi.os, 'close'))
        return write, read, close

    def testFixtureFinalVerificationKeepsReadAndNestedRetirementFailures(self):
        original = OSError(errno.ENOSPC, 'FIRST_VERIFICATION_READ')
        with ExitStack() as stack:
            write, read, close = self.fixture_creation_io(stack)
            read.side_effect = original
            def close_descriptor(fd):
                if fd >= 20: raise OSError(errno.EINTR, 'CLOSE_' + str(fd))
            close.side_effect = close_descriptor
            with self.assertRaises(ob.RetirementFailure) as caught: fi.create_owned_fixture()
            self.assertIs(first_error(caught.exception), original)
            self.assertEqual([row['descriptor'] for row in close_records(caught.exception)], [20, 22, 21])
            self.assertEqual([call.args[0] for call in close.call_args_list], [14, 13, 12, 11, 10, 22, 21, 20])
            self.assertEqual(write.call_count, 2); read.assert_called_once()

    def testFixtureWriteStopsWithinBothAbsoluteBudgets(self):
        for limit in (720, 900):
            with self.subTest(limit=limit), budget_at(limit) as (clock, check), ExitStack() as stack:
                write, read, close = self.fixture_creation_io(stack)
                def partial(fd, data): clock[0] += 2; return 1
                write.side_effect = partial
                with self.assertRaisesRegex(pc.Refusal, 'deadline'): fi.create_owned_fixture(check=check)
                write.assert_called_once(); read.assert_not_called()
                self.assertEqual([call.args[0] for call in close.call_args_list], [13, 12, 11, 10])

    def testFixtureVerificationStopsWithinBothAbsoluteBudgets(self):
        for limit in (720, 900):
            with self.subTest(limit=limit), budget_at(limit) as (clock, check), ExitStack() as stack:
                write, read, close = self.fixture_creation_io(stack)
                def partial(fd, count): clock[0] += 2; return pc.SELECTED
                read.side_effect = partial
                with self.assertRaisesRegex(pc.Refusal, 'deadline'): fi.create_owned_fixture(check=check)
                self.assertEqual(write.call_count, 2); read.assert_called_once()
                self.assertEqual([call.args[0] for call in close.call_args_list], [14, 13, 12, 11, 10, 22, 21, 20])

    def testRootCreationFailureKeepsFirstErrorAndAmbiguousClose(self):
        original = OSError(errno.ENOSPC, 'FIRST_ROOT_FSTAT')
        with patch.object(ob.sys, 'platform', 'darwin'), \
             patch.object(ob.tempfile, 'mkdtemp', return_value=ROOT), \
             patch.object(ob.os, 'open', return_value=10), \
             patch.object(ob.os, 'fstat', side_effect=original), \
             patch.object(ob.os, 'close', side_effect=OSError(errno.EINTR, 'ROOT_CLOSE')) as close:
            with self.assertRaises(ob.RetirementFailure) as caught: ob.OwnedBuild.create()
        self.assertIs(caught.exception.original, original)
        self.assertEqual(caught.exception.cleanup_failures[0]['errno'], errno.EINTR)
        close.assert_called_once_with(10)

    def testLedgerFailureEvidenceIsBoundedButAllClosesAreAttemptedOnce(self):
        ledger = ob._Descriptors()
        for descriptor in range(300): ledger.acquire(lambda descriptor=descriptor: descriptor)
        with patch.object(ob.os, 'close', side_effect=OSError(errno.EINTR, 'x' * 2000)) as close:
            with self.assertRaises(ob.RetirementFailure) as caught: ledger.finish()
            with self.assertRaises(ob.RetirementFailure): ledger.finish()
        self.assertEqual(close.call_count, 300)
        self.assertEqual(len(caught.exception.cleanup_failures), 256)
        self.assertEqual(caught.exception.omitted_cleanup_failure_count, 44)
        self.assertTrue(all(len(row['message']) <= 512 for row in caught.exception.cleanup_failures))
        self.assertEqual(ledger.owned, [])

    def testSourceWriteStopsInsideBothAbsoluteBudgetsAndStillCloses(self):
        for limit in (720, 900):
            with self.subTest(limit=limit), budget_at(limit) as (clock, check), ExitStack() as stack:
                owner, close = self.source_owner(stack)
                stack.enter_context(patch.object(ec.os, 'mkdir'))
                stack.enter_context(patch.object(ec.os, 'open', side_effect=[10, 11, 12]))
                def write(fd, data): clock[0] += 2; return 1
                write = stack.enter_context(patch.object(ec.os, 'write', side_effect=write))
                sync = stack.enter_context(patch.object(ec.os, 'fsync'))
                with self.assertRaisesRegex(pc.Refusal, 'deadline'):
                    ec._write_inputs(owner, {'Host/main.swift': b'xyz'}, check=check)
                write.assert_called_once(); sync.assert_not_called()
                owner.close()
                self.assertEqual([call.args[0] for call in close.call_args_list], [12, 11, 10, 5])

    def testSourceReadStopsInsideBothAbsoluteBudgetsAndStillCloses(self):
        for limit in (720, 900):
            with self.subTest(limit=limit), budget_at(limit) as (clock, check), ExitStack() as stack:
                owner, close = self.source_owner(stack)
                stack.enter_context(patch.object(ec.os, 'open', side_effect=[10, 11, 12]))
                def read(fd, amount): clock[0] += 2; return b'x'
                read = stack.enter_context(patch.object(ec.os, 'read', side_effect=read))
                with self.assertRaisesRegex(pc.Refusal, 'deadline'):
                    ec._verify_inputs(owner, (('Host/main.swift', hashlib.sha256(b'x').hexdigest()),), check=check)
                read.assert_called_once(); owner.close()
                self.assertEqual([call.args[0] for call in close.call_args_list], [12, 11, 10, 5])

    def testConfigurationReadStopsInsideBothAbsoluteBudgets(self):
        for limit in (720, 900):
            with self.subTest(limit=limit), budget_at(limit) as (clock, check), ExitStack() as stack:
                owner, close = self.source_owner(stack)
                stack.enter_context(patch.object(ob.os, 'open', side_effect=[10, 12]))
                def read(fd, amount): clock[0] += 2; return b'x'
                read = stack.enter_context(patch.object(ob.os, 'read', side_effect=read))
                with self.assertRaisesRegex(pc.Refusal, 'deadline'):
                    owner.read_configuration('Owned.xctestrun', check=check)
                read.assert_called_once(); owner.close()
                self.assertEqual([call.args[0] for call in close.call_args_list], [12, 10, 5])

    def testBoundConfigurationWriteStopsWithinBothAbsoluteBudgets(self):
        for limit in (720, 900):
            with self.subTest(limit=limit), budget_at(limit) as (clock, check), ExitStack() as stack:
                owner, close = self.source_owner(stack)
                _, inspection, _ = model()
                binding = inspection.runner_binding
                original = binding.original.raw
                root = metadata(5, stat.S_IFDIR | 0o700)
                product = metadata(10, stat.S_IFDIR | 0o700)
                original_metadata = metadata(11, size=len(original))
                created = metadata(12, size=0)
                stack.enter_context(patch.object(ob.os, 'fstat', side_effect=lambda fd: {5: root, 10: product, 11: original_metadata, 12: created}[fd]))
                stack.enter_context(patch.object(ob.os, 'open', side_effect=[10, 11, 10, 12]))
                stack.enter_context(patch.object(ob.os, 'read', side_effect=[original, b'']))
                def write(fd, data): clock[0] += 2; return 1
                write = stack.enter_context(patch.object(ec.os, 'write', side_effect=write))
                sync = stack.enter_context(patch.object(ec.os, 'fsync'))
                with self.assertRaisesRegex(pc.Refusal, 'deadline'):
                    ec._write_bound_configuration(owner, binding, check=check)
                write.assert_called_once(); sync.assert_not_called(); owner.close()
                self.assertEqual([call.args[0] for call in close.call_args_list], [11, 10, 12, 10, 5])

    def testConfigurationEnumerationChecksBudgetAfterEachEntry(self):
        with budget_at(720) as (clock, check), ExitStack() as stack:
            workspace, close = self.source_owner(stack)
            subject, _, _ = model()
            subject.workspace = workspace
            subject._build_admission = check.__self__
            stack.enter_context(patch.object(ob.os, 'open', return_value=10))
            class SlowEntries(Entries):
                def __next__(self):
                    value = super().__next__(); clock[0] += 2; return value
            entries = SlowEntries(['Owned.xctestrun', 'later.xctestrun'])
            stack.enter_context(patch.object(ob.os, 'scandir', return_value=entries))
            with self.assertRaisesRegex(pc.Refusal, 'deadline'): subject._configuration_name()
            self.assertTrue(entries.closed)
            self.assertEqual(next(entries.names), 'later.xctestrun')
            subject.close()
            self.assertEqual([call.args[0] for call in close.call_args_list], [10, 5])

    def testInventoryCannotResetEitherWholeAttemptBudget(self):
        for limit in (720, 900):
            with self.subTest(limit=limit), budget_at(limit) as (clock, check), ExitStack() as stack:
                owner, close = self.source_owner(stack)
                stack.enter_context(patch.object(ob.time, 'monotonic', side_effect=lambda: clock[0]))
                stack.enter_context(patch.object(ob.os, 'open', side_effect=[10, 12]))
                entries = Entries(['file'])
                stack.enter_context(patch.object(ob.os, 'scandir', return_value=entries))
                read_times = []
                def read(fd, amount): read_times.append(clock[0]); clock[0] += 2; return b'x'
                stack.enter_context(patch.object(ob.os, 'read', side_effect=read))
                with self.assertRaisesRegex(pc.Refusal, 'deadline'): owner.inventory(check=check)
                self.assertEqual(read_times, [limit - 1]); self.assertTrue(entries.closed)
                owner.close()
                self.assertEqual([call.args[0] for call in close.call_args_list], [12, 10, 5])

    def testInventoryKeepsItsShorterLocalCeiling(self):
        clock = [100.0]
        with ExitStack() as stack:
            owner, close = self.source_owner(stack)
            stack.enter_context(patch.object(ob.time, 'monotonic', side_effect=lambda: clock[0]))
            stack.enter_context(patch.object(ob.os, 'open', side_effect=[10, 12]))
            stack.enter_context(patch.object(ob.os, 'scandir', return_value=Entries(['file'])))
            def read(fd, amount): clock[0] += 31; return b'x'
            read = stack.enter_context(patch.object(ob.os, 'read', side_effect=read))
            with self.assertRaisesRegex(pc.Refusal, 'product observation time budget'):
                owner.inventory(check=lambda: pc.require(clock[0] < 900, 'outer deadline'))
            read.assert_called_once(); owner.close()
            self.assertEqual(close.call_count, 3)

    def testEnumerationFailureKeepsOriginalAndBothIndependentCloseErrors(self):
        original = OSError(errno.ENOSPC, 'FIRST_ENUMERATION')
        class FailedEntries(Entries):
            def __next__(self): raise original
            def close(self): self.closed = True; raise OSError(errno.EINTR, 'ENUMERATION_CLOSE')
        entries = FailedEntries([])
        with ExitStack() as stack:
            owner, close = self.source_owner(stack)
            stack.enter_context(patch.object(ob.os, 'open', return_value=10))
            stack.enter_context(patch.object(ob.os, 'scandir', return_value=entries))
            close.side_effect = OSError(errno.EINTR, 'DESCRIPTOR_CLOSE')
            with self.assertRaises(ob.RetirementFailure) as caught: owner.inventory()
            self.assertIs(first_error(caught.exception), original)
            self.assertEqual([row['errno'] for row in close_records(caught.exception)], [errno.EINTR, errno.EINTR])
            close.assert_called_once_with(10); self.assertTrue(entries.closed)
            with self.assertRaises(ob.RetirementFailure): owner.close()

    def testExpiredBudgetRefusesBeforeAnyNewRootOrFileOpen(self):
        def expired(): raise pc.Refusal('expired deadline')
        with patch.object(ob.sys, 'platform', 'darwin'), \
             patch.object(ob.tempfile, 'mkdtemp') as create, patch.object(ob.os, 'open') as opened:
            with self.assertRaises(pc.Refusal): ob.OwnedBuild.create(check=expired)
            with self.assertRaises(pc.Refusal): fi.create_owned_fixture(check=expired)
        create.assert_not_called(); opened.assert_not_called()

    def testAdmittedPreparationThreadsWorkCallbackBeforeFixtureCreation(self):
        files = {name: b'x' for name, digest in profile.HOST_ROWS}
        workspace = Mock(); workspace.path = ROOT; workspace.products_path = ROOT + '/Products'
        fixture = Mock(); fixture.claim = b'{}'
        with patch.object(profile, 'BUILD_ONLY_ENABLED', True), \
             patch.object(profile, 'HOST_ROWS', ec._source_files(files)), \
             patch.object(ob.OwnedBuild, 'create', return_value=workspace) as create, \
             patch.object(fi, 'create_owned_fixture', return_value=fixture) as create_fixture, \
             patch.object(fi, 'render_claimed_inputs', return_value={}), \
             patch.object(ec, '_write_inputs') as write:
            admission = ba._issue(0, lambda: 1)
            owner = ec.Experiment.prepare(profile.HOST_SOURCE_COMMIT, files, admission=admission)
            for operation in (create, workspace.create_products_directory, workspace.create_captures_directory,
                              create_fixture, write):
                self.assertEqual(operation.call_args.kwargs['check'], admission.work_check)
            owner.close()

    def testAdmittedPreparationPreservesActualWriteAndIndependentOwnerCloses(self):
        files = {name: b'x' for name, digest in profile.HOST_ROWS}
        original = OSError(errno.ENOSPC, 'FIRST_PREPARATION_WRITE')
        with ExitStack() as stack:
            workspace, close = self.source_owner(stack)
            fixture = fi.PreparedFixture(fi._FIXTURE_KEY, FIXTURE_ROOT, b'{}', 6)
            stack.enter_context(patch.object(profile, 'BUILD_ONLY_ENABLED', True))
            stack.enter_context(patch.object(profile, 'HOST_ROWS', ec._source_files(files)))
            stack.enter_context(patch.object(ob.OwnedBuild, 'create', return_value=workspace))
            stack.enter_context(patch.object(workspace, 'create_products_directory'))
            stack.enter_context(patch.object(workspace, 'create_captures_directory', return_value={'device': 1, 'inode': 50}))
            stack.enter_context(patch.object(fi, 'create_owned_fixture', return_value=fixture))
            stack.enter_context(patch.object(fi, 'render_claimed_inputs', return_value={}))
            stack.enter_context(patch.object(ec.os, 'mkdir'))
            stack.enter_context(patch.object(ec.os, 'open', side_effect=[10, 11, 12]))
            stack.enter_context(patch.object(ec.os, 'write', side_effect=original))
            close.side_effect = lambda fd: (_ for _ in ()).throw(OSError(errno.EINTR, 'CLOSE_' + str(fd)))
            admission = ba._issue(0, lambda: 1)
            with self.assertRaises(ec.PreparationFailure) as caught:
                ec.Experiment.prepare(profile.HOST_SOURCE_COMMIT, files, admission=admission)
            self.assertIs(first_error(caught.exception), original)
            self.assertEqual(caught.exception.dispositions, {'fixture': 'unproved:RetirementFailure', 'workspace': 'unproved:RetirementFailure'})
            self.assertEqual([row['descriptor'] for row in close_records(caught.exception) if 'descriptor' in row], [6, 5, 12, 11, 10])
            self.assertEqual([call.args[0] for call in close.call_args_list], [12, 11, 10, 6, 5])
            self.assertEqual(admission.state, 'retired')
            fixture.close(); workspace.close()
            self.assertEqual(close.call_count, 5)

    def testFailureDispositionPropagatesFinalisationBudgetInsideActualInventory(self):
        with budget_at(900) as (clock, check), ExitStack() as stack:
            workspace, close = self.source_owner(stack)
            subject = check.__self__
            subject.workspace = workspace
            subject.input_rows = ()
            stack.enter_context(patch.object(ob.time, 'monotonic', side_effect=lambda: clock[0]))
            stack.enter_context(patch.object(ob.os, 'open', side_effect=[10, 12]))
            stack.enter_context(patch.object(ob.os, 'scandir', return_value=Entries(['file'])))
            def read(fd, amount): clock[0] += 2; return b'x'
            read = stack.enter_context(patch.object(ob.os, 'read', side_effect=read))
            subject._record_b_failure(pc.Refusal('original build failure'))
            self.assertEqual(subject.failure_evidence['partial_products'], 'unproved:Refusal')
            self.assertEqual(subject.failure_evidence['partial_captures'], 'unproved:Refusal')
            read.assert_called_once()
            subject.close()
            self.assertEqual([call.args[0] for call in close.call_args_list], [12, 10, 5])


if __name__ == '__main__':
    unittest.main()
