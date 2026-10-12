"""Every subprocess, FD, signal, selector and clock operation is mocked."""
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch
import errno
import unittest

import bounded_process as bp
import probe_contract as pc

ARGS = ('/usr/bin/codesign', '--verify', '/synthetic-owned')
CWD = '/private/tmp/disk-selection-build-memory'

class Pipe:
    def __init__(self, fd):
        self.fd = fd; self.closed = False
    def fileno(self): return self.fd
    def close(self): self.closed = True

class Selector:
    def __init__(self): self.keys = {}; self.closed = False
    def register(self, stream, _, data): self.keys[stream.fd] = SimpleNamespace(fileobj=stream, data=data)
    def unregister(self, stream): self.keys.pop(stream.fd)
    def get_map(self): return self.keys
    def select(self, _): return [(key, 1) for key in tuple(self.keys.values())]
    def close(self): self.closed = True

class Child:
    def __init__(self):
        self.pid = 1001
        self.stdout = Pipe(31); self.stderr = Pipe(32); self.returncode = None
        self.terminate = Mock(side_effect=lambda: setattr(self, 'returncode', -15))
        self.kill = Mock(side_effect=lambda: setattr(self, 'returncode', -9))
    def poll(self): return self.returncode

class BoundedProcessTests(unittest.TestCase):
    def execute(self, chunks=None, *, child=None, cancelled=lambda: False, max_output=100, configure=None):
        child = child or Child(); selector = Selector(); clock = [0.0]; eof = set()
        queues = chunks or {31: [b'ok', b''], 32: [b'warning', b'']}
        def read(fd, _):
            item = queues[fd].pop(0) if queues[fd] else b''
            if isinstance(item, BaseException): raise item
            if not item:
                eof.add(fd)
                if len(eof) == 2: child.returncode = 0
            return item
        def now(): clock[0] += 0.1; return clock[0]
        with ExitStack() as stack:
            popen = stack.enter_context(patch.object(bp.subprocess, 'Popen', return_value=child))
            stack.enter_context(patch.object(bp.selectors, 'DefaultSelector', return_value=selector))
            stack.enter_context(patch.object(bp.os, 'set_blocking'))
            stack.enter_context(patch.object(bp.os, 'killpg', side_effect=ProcessLookupError(errno.ESRCH,'synthetic')))
            stack.enter_context(patch.object(bp.os, 'read', side_effect=read))
            stack.enter_context(patch.object(bp.time, 'monotonic', side_effect=now))
            stack.enter_context(patch.object(bp.time, 'sleep'))
            if configure: configure(stack, child, selector)
            try:
                result = bp.run(ARGS, cwd=CWD, environment={'PATH': '/usr/bin'}, timeout=1,
                                cancelled=cancelled, max_output=max_output)
            except bp.ProcessFailure as error: result = error
        return result, child, selector, popen

    def testNormalShortWritesEOFAndNoInheritedDescriptors(self):
        result, child, selector, popen = self.execute()
        self.assertIsInstance(result, bp.ProcessResult)
        self.assertEqual((result.stdout, result.stderr), (b'ok', b'warning'))
        self.assertTrue(result.direct_child_reaped and result.owned_group_retired and child.stdout.closed and child.stderr.closed and selector.closed)
        self.assertTrue(popen.call_args.kwargs['close_fds'])
        self.assertFalse(popen.call_args.kwargs['shell'])
        self.assertEqual(popen.call_args.kwargs['env'], {'PATH': '/usr/bin'})
        self.assertNotIn('pass_fds', popen.call_args.kwargs)
        child.terminate.assert_not_called(); child.kill.assert_not_called()

    def testEINTRAndEAGAINPreserveExactBytes(self):
        result, *_ = self.execute({31: [InterruptedError(), BlockingIOError(), b'ok', b''], 32: [b'', b'']})
        self.assertIsInstance(result, bp.ProcessResult); self.assertEqual(result.stdout, b'ok')

    def testOutputOverflowRetainsBoundedPrefixAndReapsChild(self):
        error, child, *_ = self.execute({31: [b'123456'], 32: [b'']}, max_output=4)
        self.assertIsInstance(error, bp.ProcessFailure)
        self.assertEqual(error.result.reason, 'tool-output-overflow'); self.assertEqual(error.result.stdout, b'1234')
        self.assertTrue(error.result.direct_child_reaped); child.terminate.assert_called_once()

    def testStalledPipeDeadlineDoesNotBlockOrClaimSuccess(self):
        error, child, *_ = self.execute(configure=lambda s,c,q: s.enter_context(patch.object(q, 'select', return_value=[])))
        self.assertEqual(error.result.reason, 'tool-deadline'); self.assertTrue(error.result.direct_child_reaped)
        child.terminate.assert_called_once()

    def testCancellationBeforeSpawnCreatesNoProcess(self):
        with patch.object(bp.subprocess, 'Popen') as popen:
            with self.assertRaises(bp.ProcessFailure) as caught:
                bp.run(ARGS, cwd=CWD, environment={}, timeout=1, cancelled=lambda: True)
            self.assertEqual(caught.exception.result.reason, 'cancelled-before-start'); popen.assert_not_called()

    def testCancellationAfterSpawnRetiresOwnedChild(self):
        calls = [False, True]
        error, child, *_ = self.execute(cancelled=lambda: calls.pop(0) if calls else True)
        self.assertTrue(error.result.cancelled and error.result.direct_child_reaped); child.terminate.assert_called_once()

    def testPartialSetupFailureClosesBothPipesAndReaps(self):
        error, child, selector, _ = self.execute(configure=lambda s,c,q: s.enter_context(patch.object(bp.os, 'set_blocking', side_effect=OSError(errno.EIO,'synthetic'))))
        self.assertTrue(error.result.reason.startswith('tool-owner-error'))
        self.assertTrue(child.stdout.closed and child.stderr.closed and selector.closed and error.result.direct_child_reaped)

    def testFailedSpawnHandoffIsNotReportedAsReaped(self):
        with patch.object(bp.subprocess, 'Popen', side_effect=OSError(errno.EIO,'synthetic')):
            with self.assertRaises(bp.ProcessFailure) as caught:
                bp.run(ARGS, cwd=CWD, environment={}, timeout=1)
            self.assertFalse(caught.exception.result.direct_child_reaped)

    def testUnreapedChildRefusesAfterBoundedKillAttempt(self):
        def configure(stack, child, selector):
            child.terminate.side_effect = None; child.kill.side_effect = None
            stack.enter_context(patch.object(selector, 'select', return_value=[]))
        error, child, *_ = self.execute(configure=configure)
        self.assertEqual(error.result.reason, 'direct-child-retirement-unproved')
        self.assertFalse(error.result.direct_child_reaped)
        child.terminate.assert_called_once(); child.kill.assert_called_once()

    def testOnePipeCloseFailureDoesNotSkipOtherRetirement(self):
        child = Child(); child.stdout.close = Mock(side_effect=OSError(errno.EINTR,'synthetic'))
        error, child, selector, _ = self.execute(child=child)
        self.assertEqual(error.result.reason, 'pipe-retirement-unproved')
        self.assertTrue(child.stderr.closed and selector.closed); child.stdout.close.assert_called_once()

    def testServiceProcessRetirementRequiresObservedAbsence(self):
        with patch.object(bp.os, 'kill', side_effect=ProcessLookupError(errno.ESRCH,'synthetic')) as kill:
            self.assertEqual(bp.prove_retired((101, 102)), (101, 102))
            self.assertTrue(all(call.args[1] == 0 for call in kill.call_args_list))

    def testAliveOrInaccessibleServiceProcessNeverGetsKilled(self):
        clock = iter([0, 0.1, 1.1])
        with patch.object(bp.os,'kill') as kill, patch.object(bp.time,'monotonic',side_effect=lambda:next(clock)), patch.object(bp.time,'sleep'):
            with self.assertRaisesRegex(pc.Refusal,'still-present'): bp.prove_retired((101,),timeout=1)
            kill.assert_called_once_with(101,0)
        with patch.object(bp.os,'kill',side_effect=PermissionError(errno.EPERM,'synthetic')):
            with self.assertRaisesRegex(pc.Refusal,'inconclusive'): bp.prove_retired((101,))

    def testUnapprovedToolAndRootRefuseBeforeSpawn(self):
        with patch.object(bp.subprocess,'Popen') as popen:
            for args,cwd in [(('/bin/sh','-c','anything'),CWD),(ARGS,'/Users/synthetic')]:
                with self.assertRaises(pc.Refusal): bp.run(args,cwd=cwd,environment={},timeout=1)
            popen.assert_not_called()

    def testLiveOwnedProcessGroupRefusesEvenAfterDirectChildReap(self):
        error,child,*_=self.execute(configure=lambda s,c,q:s.enter_context(patch.object(bp.os,'killpg',return_value=None)))
        self.assertTrue(error.result.direct_child_reaped)
        self.assertFalse(error.result.owned_group_retired)
        self.assertEqual(error.result.reason,'owned-process-group-retirement-unproved')

if __name__ == '__main__': unittest.main()
