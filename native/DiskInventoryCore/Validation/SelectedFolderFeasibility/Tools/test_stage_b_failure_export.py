"""Real first-disposition recorder plus entirely mocked packet/owner boundaries."""
import errno
import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch

import experiment_controller as ec
import stage_b_driver as driver
import stage_b_profile as profile
import test_stage_b_driver as dt
from test_experiment_controller import model


class FirstFailureExportTests(unittest.TestCase):
    def recorded(self, process=None):
        subject, inspection, details = model()
        if process is not None:
            subject.trace = [process]
        with patch.object(subject.fixture, 'verify', side_effect=OSError('FIRST_FIXTURE_FAILURE')), \
             patch.object(ec, '_verify_inputs', side_effect=FileNotFoundError('FIRST_SOURCE_FAILURE')), \
             patch.object(subject.workspace, 'inventory', side_effect=[('FIRST_PRODUCT_RECORD',), ('FIRST_CAPTURE_RECORD',)]):
            subject._record_b_failure(ec.pc.Refusal('first build failure'))
        self.assertEqual(subject.failure_evidence['fixture'], 'unproved:OSError')
        self.assertEqual(subject.failure_evidence['source'], 'unproved:FileNotFoundError')
        with patch.object(dt, 'model', return_value=(subject, inspection, details)):
            result = dt.DriverTests().run_model(('build',))
        packet = {call.args[0]: call.args[1] for call in result[3].add.call_args_list}
        return result, packet

    def testFirstDispositionSurvivesLaterSuccessfulRecheck(self):
        result, packet = self.recorded()
        self.assertEqual(result[0], 2)
        first = json.loads(packet['first-failure.json'])
        later = json.loads(packet['dispositions.json'])
        self.assertEqual(first['fixture'], 'unproved:OSError')
        self.assertEqual(first['source'], 'unproved:FileNotFoundError')
        self.assertEqual(first['partial_products'], ['FIRST_PRODUCT_RECORD'])
        self.assertEqual(first['partial_captures'], ['FIRST_CAPTURE_RECORD'])
        self.assertEqual(later['fixture'], 'verified')
        self.assertEqual(later['products'], [])
        self.assertEqual(first['tool_result_indices'], [])

    def testFirstFailureRawProcessBytesExportOnceWithIndexedMetadata(self):
        process = ec.bp.ProcessResult(('/usr/bin/codesign',), b'$x `raw`\x00\xff', b'failure\n', 1, True, False, 'nonzero', True)
        result, packet = self.recorded(process)
        self.assertEqual(result[0], 2)
        self.assertEqual(packet['tool-00-stdout.bin'], process.stdout)
        self.assertEqual(packet['tool-00-stderr.bin'], process.stderr)
        first = json.loads(packet['first-failure.json'])
        self.assertEqual(first['tool_result_indices'], [0])
        self.assertNotIn('tool_results', first)
        self.assertEqual(len(json.loads(packet['tool-results.json'])), 1)
        self.assertEqual(sum(name.endswith('-stdout.bin') for name in packet), 1)

    def testRepeatedFirstProcessReferenceDoesNotDuplicateRawFiles(self):
        subject, inspection, details = model()
        process = ec.bp.ProcessResult(('/usr/bin/codesign',), b'raw', b'', 1, True, False, 'failed', True)
        subject.failure_evidence = {'stage': 'B', 'tool_results': (process, process), 'untraced_failure_result': process}
        with patch.object(dt, 'model', return_value=(subject, inspection, details)):
            result = dt.DriverTests().run_model(('build',))
        packet = {call.args[0]: call.args[1] for call in result[3].add.call_args_list}
        self.assertEqual(json.loads(packet['first-failure.json'])['tool_result_indices'], [0, 0, 0])
        self.assertEqual(sum(name.endswith('-stdout.bin') for name in packet), 1)

    def testNoReportOwnerStillRetainsOriginalErrnoAndMessage(self):
        identity = {'GITHUB_REPOSITORY': profile.REPOSITORY, 'GITHUB_REF': profile.REF,
            'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '1',
            'GITHUB_RUN_ID': '123', 'GITHUB_SHA': 'a'*40}
        admission = Mock(); output = StringIO()
        with patch.object(profile, 'BUILD_ONLY_ENABLED', True), \
             patch.object(ec, '_source_files', return_value=profile.HOST_ROWS), \
             patch.object(driver.ba, '_issue', return_value=admission), \
             patch.object(driver.sr.Report, 'create', side_effect=OSError(errno.ENOSPC, 'FIRST_REPORT_ENOSPC')), \
             patch.object(driver.time, 'monotonic', return_value=1), redirect_stdout(output):
            code = driver.run(identity, {}, started_at=0)
        raw = output.getvalue(); self.assertLessEqual(len(raw.encode()), 16384)
        record = json.loads(raw.removeprefix('OWNED_BUILD_TERMINAL '))
        self.assertEqual(code, 2); self.assertIsNone(record['report_path'])
        self.assertEqual(record['failures'][0]['errno'], errno.ENOSPC)
        self.assertIn('FIRST_REPORT_ENOSPC', record['failures'][0]['message'])
        self.assertEqual(record['omitted_failure_count'], 0)
        admission.retire.assert_called_once()

    def testRealSourceWriteAndThreeCloseFailuresKeepOriginalProjection(self):
        workspace = Mock(); workspace._descriptor = 5
        original = OSError(errno.ENOSPC, 'FIRST_WRITE_ENOSPC')
        with patch.object(ec.os, 'mkdir'), patch.object(ec.os, 'open', side_effect=[10, 11, 12]), \
             patch.object(ec.os, 'write', side_effect=original), \
             patch.object(ec.os, 'close', side_effect=OSError(errno.EINTR, 'CLOSE_EINTR')) as close:
            with self.assertRaises(ec.ob.RetirementFailure) as caught:
                ec._write_inputs(workspace, {'Host/main.swift': b'x'})
        projected = driver.error_record('prepare-or-build', caught.exception)
        self.assertEqual(projected['kind'], 'OSError')
        self.assertEqual(projected['errno'], errno.ENOSPC)
        self.assertIn('FIRST_WRITE_ENOSPC', projected['message'])
        self.assertEqual([row['descriptor'] for row in projected['cleanup_failures']], [12, 11, 10])
        self.assertTrue(all(row['errno'] == errno.EINTR for row in projected['cleanup_failures']))
        self.assertEqual([call.args[0] for call in close.call_args_list], [12, 11, 10])
        self.assertEqual(driver.terminal_failures([projected])[0]['errno'], errno.ENOSPC)

    def testDriverPassesOneAbsoluteFinalisationCheckToOwnerOperations(self):
        code, record, subject, report, order = dt.DriverTests().run_model()
        self.assertEqual(code, 0)
        check = subject.fixture.verify.call_args.kwargs['check']
        for call in subject.workspace.inventory.call_args_list:
            self.assertIs(call.kwargs['check'], check)
        with patch.object(driver.time, 'monotonic', return_value=899): check()
        with patch.object(driver.time, 'monotonic', return_value=900):
            with self.assertRaisesRegex(ec.pc.Refusal, 'finalisation deadline'): check()

    def testTerminalProjectionBoundsEscapedUnicodeAndKeepsFirst(self):
        for text in ('\x00'*2000, '😀'*2000, '\\"'*2000):
            failures = [dict(phase=text, kind=text, reason=text, message=text, errno=28) for _ in range(100)]
            result = driver.terminal_failures(failures)
            self.assertTrue(result); self.assertLessEqual(len(result), 16)
            self.assertEqual(result[0]['errno'], 28)
            self.assertLessEqual(len(driver.encode(result)), 14000)
            self.assertLessEqual(len(result[0]['message'].encode()), 512)


if __name__ == '__main__':
    unittest.main()
