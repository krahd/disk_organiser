"""Memory/mock tests only: no report, fixture, process or native owner is run."""
from contextlib import ExitStack
from copy import copy
import errno
import hashlib
import json
import os
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import owned_build_observation as ob
import probe_contract as pc
import stage_b_receipt as receipt

ROOT = receipt.REPORT_PREFIX + "synthetic"
WORKSPACE = "/private/tmp/disk-selection-build-synthetic"
OUTCOME = b'{"outcome":"candidate_pass","source_owners":"closed"}'


def metadata(inode, mode=stat.S_IFREG | 0o600, size=0):
    return SimpleNamespace(st_dev=1, st_ino=inode, st_mode=mode, st_uid=501, st_gid=20,
                           st_size=size, st_nlink=1, st_mtime_ns=1, st_ctime_ns=1)


class Entries:
    def __init__(self, names):
        self.names = iter(names)
        self.closed = False

    def __enter__(self):
        return self

    def __iter__(self):
        return self

    def __next__(self):
        return SimpleNamespace(name=next(self.names))

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.closed = True


class MemoryFS:
    """Fake descriptors and bytes; every OS boundary below is patched."""
    def __init__(self):
        self.nodes = {ROOT: metadata(10, stat.S_IFDIR | 0o700),
                      WORKSPACE: metadata(100, stat.S_IFDIR | 0o700),
                      "Products": metadata(101, stat.S_IFDIR | 0o700)}
        self.fds = {10: ROOT, 100: WORKSPACE, 101: "Products"}
        self.data, self.positions = {}, {}
        self.closed, self.events, self.iterators = [], [], []
        self.next_fd = 200
        self.write_size = None
        self.write_error = self.read_error = None
        self.close_errors = {}
        self.now = 1
        self.after_close = None
        self.config_names = []
        self.overrides = {}

    def stat(self, name, *, dir_fd=None, follow_symlinks=True):
        if name in self.overrides:
            return copy(self.overrides[name])
        if name not in self.nodes:
            raise FileNotFoundError(name)
        return copy(self.nodes[name])

    def fstat(self, descriptor):
        return copy(self.nodes[self.fds[descriptor]])

    def open(self, name, flags, mode=None, *, dir_fd=None):
        self.events.append(("open", name, flags, dir_fd))
        if name == ROOT:
            return 10
        if name == "Products":
            return 101
        if flags & os.O_CREAT:
            if name in self.nodes:
                raise FileExistsError(name)
            self.nodes[name] = metadata(self.next_fd)
            self.data[name] = b""
            self.nodes[ROOT].st_mtime_ns += 1
            self.nodes[ROOT].st_ctime_ns += 1
        if name not in self.nodes:
            raise FileNotFoundError(name)
        fd = self.next_fd
        self.next_fd += 1
        self.fds[fd] = name
        self.positions[fd] = 0
        return fd

    def write(self, descriptor, data):
        self.events.append(("write", self.fds[descriptor]))
        if self.write_error:
            raise self.write_error
        amount = len(data) if self.write_size is None else min(self.write_size, len(data))
        name = self.fds[descriptor]
        self.data[name] += bytes(data[:amount])
        self.nodes[name].st_size = len(self.data[name])
        self.nodes[name].st_mtime_ns += 1
        self.nodes[name].st_ctime_ns += 1
        return amount

    def read(self, descriptor, maximum):
        self.events.append(("read", self.fds[descriptor], maximum))
        if self.read_error:
            raise self.read_error
        name, position = self.fds[descriptor], self.positions[descriptor]
        data = self.data[name][position:position + maximum]
        self.positions[descriptor] += len(data)
        return data

    def lseek(self, descriptor, offset, whence):
        self.positions[descriptor] = offset
        return offset

    def close(self, descriptor):
        self.events.append(("close", descriptor))
        self.closed.append(descriptor)
        if self.after_close:
            self.after_close(descriptor)
        if descriptor in self.close_errors:
            raise self.close_errors[descriptor]

    def scandir(self, descriptor):
        names = self.config_names if descriptor == 101 else list(self.data)
        iterator = Entries(names)
        self.iterators.append(iterator)
        return iterator

    def configuration(self, name="Owned.xctestrun", raw=b"vendor output"):
        self.config_names.append(name)
        self.nodes[name] = metadata(1000 + len(self.config_names), size=len(raw))
        self.data[name] = raw
        return name

    def workspace(self):
        owner = object.__new__(ob.OwnedBuild)
        owner.path, owner._descriptor, owner._identity = WORKSPACE, 100, (1, 100)
        owner._products_identity, owner._closed = (1, 101), False
        # No destructor may perform a real or extra close after patch teardown.
        owner._closed = True
        owner._admit = Mock(return_value=None)
        return owner


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.fs = MemoryFS()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.mocks = {}
        for name in ("open", "stat", "fstat", "write", "read", "lseek", "close", "scandir"):
            self.mocks[name] = self.stack.enter_context(patch.object(receipt.os, name, side_effect=getattr(self.fs, name)))
        self.stack.enter_context(patch.object(receipt.os, "getuid", return_value=501))
        self.stack.enter_context(patch.object(receipt.sys, "platform", "darwin"))
        self.mktemp = self.stack.enter_context(patch.object(receipt.tempfile, "mkdtemp", return_value=ROOT))
        self.stack.enter_context(patch.object(receipt.time, "monotonic", side_effect=lambda: self.fs.now))
        self.stack.enter_context(patch("builtins.open", side_effect=AssertionError("unmocked file owner")))

    def report(self):
        return receipt.Report.create(deadline=900)

    def testFreshFixedRootAndExclusiveNoFollowRegularFiles(self):
        report = self.report()
        report.add("log.stdout", b"hello")
        report.abort()
        self.mktemp.assert_called_once_with(prefix="disk-selection-report-", dir="/private/tmp")
        flags = self.mocks["open"].call_args_list[1].args[1]
        for expected in (os.O_EXCL, os.O_CREAT, os.O_NOFOLLOW, os.O_CLOEXEC, os.O_NONBLOCK):
            self.assertTrue(flags & expected)
        self.assertEqual(self.mocks["open"].call_args_list[1].kwargs, {"dir_fd": 10})

    def testConstructorCannotReopenAPath(self):
        with self.assertRaisesRegex(pc.Refusal, "fresh owned report"):
            receipt.Report(object(), ROOT, 10, (1, 10), 900)
        self.mocks["open"].assert_not_called()

    def testWrongPlatformAndDeadlineRefuseBeforeCreation(self):
        for platform, now in (("linux", 1), ("darwin", 900)):
            self.fs.now = now
            with patch.object(receipt.sys, "platform", platform), self.assertRaises(pc.Refusal):
                self.report()
        self.mktemp.assert_not_called()

    def testCreationReplacementAndCloseFailureBothSurvive(self):
        self.fs.overrides[ROOT] = metadata(99, stat.S_IFDIR | 0o700)
        self.fs.close_errors[10] = OSError(errno.EINTR, "ambiguous")
        with self.assertRaises(receipt.ReportFailure) as caught:
            self.report()
        self.assertEqual(len(caught.exception.failures), 2)
        self.assertEqual(caught.exception.close_disposition["status"], "unproved")
        self.assertEqual(self.fs.closed, [10])

    def testRootModeOwnerAndTypeRefuseBeforeAnyPayload(self):
        for mode, uid in ((stat.S_IFDIR | 0o755, 501), (stat.S_IFDIR | 0o700, 999),
                          (stat.S_IFLNK | 0o700, 501), (stat.S_IFREG | 0o700, 501)):
            self.fs.nodes[ROOT].st_mode, self.fs.nodes[ROOT].st_uid = mode, uid
            with self.subTest(mode=mode, uid=uid), self.assertRaises(receipt.ReportFailure):
                self.report()
        self.mocks["write"].assert_not_called()
        self.assertEqual(self.fs.closed, [10] * 4)

    def testPartialWritesPreserveRawShellCharactersAndUTF8(self):
        self.fs.write_size = 2
        raw = "raw $HOME `whoami` $(no) café\n".encode("utf-8") + b"\x00\xff"
        report = self.report()
        row = report.add("tool-000.stdout", raw)
        self.assertEqual(self.fs.data["tool-000.stdout"], raw)
        self.assertEqual(row, {"path": "tool-000.stdout", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        report.abort()

    def testManifestExcludesItselfAndReceiptFollowsAllActualCloses(self):
        report = self.report()
        report.add("payload.bin", b"original")
        final = report.finalise(OUTCOME)
        manifest = json.loads(self.fs.data["manifest.json"])
        self.assertEqual([row["path"] for row in manifest["files"]], ["outcome.json", "payload.bin"])
        self.assertEqual(final.manifest_sha256, hashlib.sha256(self.fs.data["manifest.json"]).hexdigest())
        self.assertEqual(final.manifest_bytes, len(self.fs.data["manifest.json"]))
        self.assertEqual(final.path, ROOT)
        self.assertEqual(final.outcome, "candidate_pass")
        self.assertEqual((final.root_device, final.root_inode), (1, 10))
        self.assertEqual(self.fs.events[-1], ("close", 10))
        self.assertEqual(len(self.fs.closed), 4)
        self.assertTrue(all(iterator.closed for iterator in self.fs.iterators))

    def testExplicitFailedOutcomeReturnsOnlyFailedReceipt(self):
        final = self.report().finalise(b'{"outcome":"failed"}')
        self.assertEqual(final.outcome, "failed")

    def testDuplicateUnsafeAndReservedNamesRefuseBeforeFileOpen(self):
        report = self.report()
        report.add("one.bin", b"one")
        for name in ("../bad", ".hidden", "a/b", "a\\b", "$HOME", "`x`", "one.bin", "manifest.json", "outcome.json", "é"):
            previous = self.mocks["open"].call_count
            with self.subTest(name=name), self.assertRaises(receipt.ReportFailure):
                report.add(name, b"two")
            self.assertEqual(self.mocks["open"].call_count, previous)
        report.abort()

    def testNonBytesAndByteBudgetRefuseBeforeOpen(self):
        report = self.report()
        for data in ("not raw", bytearray(b"x")):
            with self.assertRaises(receipt.ReportFailure):
                report.add("bad.bin", data)
        report._bytes = receipt.MAX_BYTES - receipt.MAX_OUTCOME_BYTES - receipt.MAX_MANIFEST_BYTES
        with self.assertRaisesRegex(receipt.ReportFailure, "packet budget"):
            report.add("large.bin", b"x")
        self.assertEqual(self.mocks["open"].call_count, 1)
        report.abort()

    def testLastPayloadByteFitsAndNextByteCannotSpendFinalisationReserve(self):
        report = self.report()
        report._bytes = receipt.MAX_BYTES - receipt.MAX_OUTCOME_BYTES - receipt.MAX_MANIFEST_BYTES - 1
        report.add("last-byte", b"x")
        with self.assertRaisesRegex(receipt.ReportFailure, "packet budget"):
            report.add("one-too-many", b"y")
        with self.assertRaises(receipt.ReportFailure) as caught:
            report.finalise(OUTCOME)
        self.assertEqual(caught.exception.path, ROOT)
        self.assertLessEqual(report._bytes, receipt.MAX_BYTES)

    def testFileBudgetReservesOutcomeAndManifestSlots(self):
        report = self.report()
        for index in range(receipt.MAX_FILES - 2):
            report.add("payload-%03d" % index, b"")
        with self.assertRaisesRegex(receipt.ReportFailure, "file-attempt"):
            report.add("overflow", b"")
        with self.assertRaises(receipt.ReportFailure) as caught:
            report.finalise(OUTCOME)
        self.assertEqual(caught.exception.path, ROOT)
        self.assertEqual(len(self.fs.data), receipt.MAX_FILES)
        self.assertEqual(json.loads(self.fs.data["outcome.json"])["outcome"], "failed")
        failed = caught.exception.receipt
        self.assertEqual(failed.outcome, "failed")
        self.assertEqual((failed.root_device, failed.root_inode), (1, 10))
        self.assertEqual(failed.manifest_sha256, hashlib.sha256(self.fs.data["manifest.json"]).hexdigest())
        self.assertEqual(failed.manifest_bytes, len(self.fs.data["manifest.json"]))

    def testRootReplacementRefusesAndStillClosesHeldRoot(self):
        report = self.report()
        self.fs.overrides[ROOT] = metadata(12, stat.S_IFDIR | 0o700)
        with self.assertRaisesRegex(receipt.ReportFailure, "root replaced"):
            report.add("payload", b"x")
        self.assertEqual(report.abort(), {"status": "closed"})
        self.assertEqual(self.fs.closed, [10])

    def testNonregularSymlinkAndHardlinkFileRefuseBeforeWrite(self):
        for mode, nlink in ((stat.S_IFIFO | 0o600, 1), (stat.S_IFLNK | 0o600, 1), (stat.S_IFREG | 0o600, 2)):
            with self.subTest(mode=mode, nlink=nlink):
                report = self.report()
                original = self.fs.open
                def altered(name, *args, **kwargs):
                    fd = original(name, *args, **kwargs)
                    self.fs.nodes[name].st_mode = mode
                    self.fs.nodes[name].st_nlink = nlink
                    return fd
                name = "case-%s-%s" % (mode, nlink)
                with patch.object(receipt.os, "open", side_effect=altered), self.assertRaisesRegex(receipt.ReportFailure, "regular"):
                    report.add(name, b"x")
                report.abort()
        self.mocks["write"].assert_not_called()

    def testZeroAndInvalidWriteCountsRefuseWithoutRetry(self):
        for index, amount in enumerate((0, -1, 99, True)):
            report = self.report()
            with patch.object(receipt.os, "write", return_value=amount) as write, self.assertRaisesRegex(receipt.ReportFailure, "write progress"):
                report.add("write-%s" % index, b"x")
            self.assertEqual(write.call_count, 1)
            report.abort()

    def testInterruptedWriteAttemptsAreFiniteAndDescriptorCloses(self):
        report = self.report()
        self.fs.write_error = InterruptedError()
        with patch.object(receipt, "MAX_ATTEMPTS", 3), self.assertRaisesRegex(receipt.ReportFailure, "write-attempt"):
            report.add("interrupted", b"x")
        self.assertEqual(self.mocks["write"].call_count, 3)
        self.assertEqual(self.fs.closed, [200])
        report.abort()

    def testWriteAndFileCloseFailureBothSurviveWithoutRetry(self):
        report = self.report()
        self.fs.write_error = OSError("first-write-failure")
        self.fs.close_errors[200] = OSError("ambiguous-close")
        with self.assertRaises(receipt.ReportFailure) as caught:
            report.add("broken", b"x")
        self.assertIn("first-write-failure", caught.exception.failures[0])
        self.assertIn("ambiguous-close", caught.exception.failures[1])
        report.abort(); report.abort()
        self.assertEqual(self.fs.closed, [200, 10])

    def testShortGrownAndChangedReadbackRefuse(self):
        for part in (b"", b"xy", b"z"):
            report = self.report()
            with patch.object(receipt.os, "read", side_effect=[part, b""]), self.assertRaises(receipt.ReportFailure):
                report.add("read-%s" % len(self.fs.data), b"x")
            report.abort()

    def testInterruptedReadAttemptsAreFinite(self):
        report = self.report()
        self.fs.read_error = InterruptedError()
        with patch.object(receipt, "MAX_ATTEMPTS", 3), self.assertRaisesRegex(receipt.ReportFailure, "read-attempt"):
            report.add("interrupted", b"x")
        self.assertEqual(self.mocks["read"].call_count, 3)
        report.abort()

    def testNamedFileReplacementAfterReadRefuses(self):
        report = self.report()
        original = self.fs.read
        def replace_after_read(fd, maximum):
            result = original(fd, maximum)
            self.fs.overrides[self.fs.fds[fd]] = metadata(999, size=1)
            return result
        with patch.object(receipt.os, "read", side_effect=replace_after_read), self.assertRaisesRegex(receipt.ReportFailure, "replaced"):
            report.add("changed", b"x")
        report.abort()

    def testPayloadMutationMissingAndUnexpectedMembersRefuseFinalReceipt(self):
        for mutation in ("changed", "missing", "extra"):
            with self.subTest(mutation=mutation):
                report = self.report()
                name = "payload-" + mutation
                report.add(name, b"x")
                if mutation == "changed":
                    self.fs.nodes[name].st_ctime_ns += 1
                elif mutation == "missing":
                    del self.fs.data[name]
                else:
                    self.fs.data["unowned"] = b""
                with self.assertRaises(receipt.ReportFailure) as caught:
                    report.finalise(OUTCOME)
                self.assertIsNone(caught.exception.path)
                self.assertEqual(caught.exception.close_disposition["status"], "closed")
                # Isolate this memory-only case for the next fresh owner.
                self.fs.data.clear()
                for key in tuple(self.fs.nodes):
                    if key not in (ROOT, WORKSPACE, "Products"):
                        del self.fs.nodes[key]

    def testFinalRootCloseFailureNeverReturnsReceiptOrSafePath(self):
        report = self.report()
        self.fs.close_errors[10] = OSError(errno.EINTR, "ambiguous")
        with self.assertRaises(receipt.ReportFailure) as caught:
            report.finalise(OUTCOME)
        self.assertIsNone(caught.exception.path)
        self.assertIsNone(caught.exception.receipt)
        self.assertEqual(caught.exception.close_disposition["status"], "unproved")
        report.abort()
        self.assertEqual(self.fs.closed.count(10), 1)

    def testOutcomeManifestAndRootCloseFailuresAllRemainVisible(self):
        report = self.report()
        self.fs.close_errors = {200: OSError("outcome-close"), 201: OSError("manifest-close"),
                                10: OSError("root-close")}
        with self.assertRaises(receipt.ReportFailure) as caught:
            report.finalise(OUTCOME)
        message = str(caught.exception)
        for expected in ("outcome-close", "manifest-close", "root-close"):
            self.assertIn(expected, message)
        self.assertEqual(self.fs.closed, [200, 201, 10])
        report.abort()
        self.assertEqual(self.fs.closed, [200, 201, 10])

    def testManifestBudgetFailureStillClosesRoot(self):
        report = self.report()
        with patch.object(receipt, "MAX_MANIFEST_BYTES", 1), self.assertRaisesRegex(receipt.ReportFailure, "manifest budget"):
            report.finalise(OUTCOME)
        self.assertEqual(self.fs.closed, [200, 10])

    def testPacketEnumerationAndIteratorCloseFailuresAreBothRetained(self):
        report = self.report()
        entries = Entries(["unexpected"])
        entries.close = Mock(side_effect=OSError("iterator-close"))
        with patch.object(receipt.os, "scandir", return_value=entries), self.assertRaises(receipt.ReportFailure) as caught:
            report.finalise(OUTCOME)
        self.assertIn("unexpected report member", caught.exception.failures[0])
        self.assertIn("iterator-close", caught.exception.failures[1])
        entries.close.assert_called_once_with()
        self.assertEqual(self.fs.closed[-1], 10)

    def testDeadlineBeforeFinalisationCreatesNothingAndStillCloses(self):
        report = self.report()
        self.fs.now = 900
        with self.assertRaises(receipt.ReportFailure) as caught:
            report.finalise(OUTCOME)
        self.assertIsNone(caught.exception.path)
        self.assertEqual(self.fs.data, {})
        self.assertEqual(self.fs.closed, [10])

    def testDeadlineDuringWriteAndAfterRootCloseCannotSucceed(self):
        report = self.report()
        original = self.fs.write
        def expire_write(fd, data):
            amount = original(fd, data)
            self.fs.now = 900
            return amount
        with patch.object(receipt.os, "write", side_effect=expire_write), self.assertRaises(receipt.ReportFailure):
            report.add("timeout", b"x")
        self.assertEqual(report.abort()["status"], "closed")
        self.fs.now = 1
        self.fs.data.clear()
        report = self.report()
        self.fs.after_close = lambda fd: setattr(self.fs, "now", 900) if fd == 10 else None
        with self.assertRaisesRegex(receipt.ReportFailure, "final-close-deadline"):
            report.finalise(OUTCOME)

    def testInvalidOutcomeAndRepeatedFinalisationCloseExactlyOnce(self):
        report = self.report()
        with self.assertRaises(receipt.ReportFailure):
            report.finalise(b'{"outcome":"success"}')
        previous = len(self.fs.closed)
        with self.assertRaises(pc.Refusal):
            report.finalise(OUTCOME)
        report.abort()
        self.assertEqual(len(self.fs.closed), previous)

    def testPartialExportCannotReturnCandidateSuccess(self):
        report = self.report()
        self.fs.write_size = 0
        with self.assertRaises(receipt.ReportFailure):
            report.add("partial", b"x")
        self.fs.write_size = None
        with self.assertRaises(receipt.ReportFailure) as caught:
            report.finalise(OUTCOME)
        self.assertEqual(json.loads(self.fs.data["outcome.json"])["outcome"], "failed")
        self.assertIsNone(caught.exception.path)
        self.assertEqual(caught.exception.close_disposition["status"], "closed")
        self.assertIsNone(caught.exception.receipt)

    def testRawMalformedAndEmptyConfigurationsArePreservedWithoutParsing(self):
        raw = "$HOME `no` $(no) café".encode() + b"\xff\x00"
        self.fs.configuration("$raw`é.xctestrun", raw)
        self.fs.configuration("Empty.xctestrun", b"")
        with patch.object(ob.xb, "parse", side_effect=AssertionError("must not parse")):
            result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
        self.assertEqual([item.data for item in result.captures], [raw, b""])
        self.assertEqual(result.failures, ())
        self.assertTrue(all(item.refusals == () for item in result.captures))
        self.assertEqual(self.fs.closed, [200, 201, 101])
        self.assertNotIn(100, self.fs.closed)

    def testRawNonregularSymlinkOversizeAndMissingAreIndependent(self):
        names = [self.fs.configuration(str(i) + ".xctestrun") for i in range(4)]
        self.fs.nodes[names[0]].st_mode = stat.S_IFIFO | 0o600
        self.fs.nodes[names[1]].st_mode = stat.S_IFLNK | 0o600
        self.fs.nodes[names[2]].st_size = receipt.MAX_CONFIGURATION_BYTES + 1
        del self.fs.nodes[names[3]]
        result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
        self.assertEqual(len(result.captures), 4)
        self.assertTrue(all(item.data is None and item.refusals for item in result.captures))
        self.assertEqual(self.mocks["open"].call_count, 1)  # Products only.
        self.mocks["read"].assert_not_called()
        self.assertEqual(self.fs.closed, [101])

    def testRawExactByteLimitAndForeignFilesystem(self):
        raw = b"x" * receipt.MAX_CONFIGURATION_BYTES
        self.fs.configuration("Exact.xctestrun", raw)
        foreign = self.fs.configuration("Foreign.xctestrun")
        self.fs.nodes[foreign].st_dev = 2
        result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
        self.assertEqual(result.captures[0].data, raw)
        self.assertIsNone(result.captures[1].data)
        self.assertTrue(result.captures[1].refusals)
        self.assertEqual(self.fs.closed, [200, 101])

    def testRawShortInterruptedAndChangingReadsRefuseAndClose(self):
        self.fs.configuration()
        for effect in ([b""], InterruptedError(), [b"vendor output", b"extra"]):
            with patch.object(receipt, "MAX_ATTEMPTS", 3), patch.object(receipt.os, "read", side_effect=effect):
                result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
            self.assertIsNone(result.captures[0].data)
            self.assertTrue(result.captures[0].refusals)
        self.assertEqual(self.fs.closed, [200, 101, 201, 101, 202, 101])

    def testRawUnsafeLeafRefusesIndependentlyBeforeOpening(self):
        self.fs.config_names = ["../escape.xctestrun", "back\\slash.xctestrun", "nul\0.xctestrun"]
        result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
        self.assertEqual(len(result.captures), 3)
        self.assertTrue(all(item.data is None and item.refusals for item in result.captures))
        self.assertEqual(self.mocks["open"].call_count, 1)

    def testRawCandidateAndEnumerationLimitsStillCaptureAdmittedLeaves(self):
        for index in range(5):
            self.fs.configuration("%s.xctestrun" % index)
        result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
        self.assertEqual(len(result.captures), 4)
        self.assertTrue(all(item.data == b"vendor output" for item in result.captures))
        self.assertIn("candidate budget", result.failures[0])

    def testRawEnumerationLimitAndMissingCandidateAreExplicit(self):
        self.fs.config_names = ["other"] * 65
        result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
        self.assertEqual(result.captures, ())
        self.assertIn("enumeration budget", result.failures[0])
        self.fs.config_names = []
        result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
        self.assertIn("no raw configuration", result.failures[0])

    def testRawEnumerationAndIteratorCloseFailuresKeepEarlierRawCandidate(self):
        name = self.fs.configuration()
        entries = Entries([name] + ["other"] * 64)
        entries.close = Mock(side_effect=OSError("iterator-close"))
        with patch.object(receipt.os, "scandir", return_value=entries):
            result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
        self.assertEqual(result.captures[0].data, b"vendor output")
        self.assertIn("enumeration budget", result.failures[0])
        self.assertIn("iterator-close", result.failures[1])
        entries.close.assert_called_once_with()
        self.assertEqual(self.fs.closed, [200, 101])

    def testRawReadAndIndependentCloseFailuresRemainVisible(self):
        self.fs.configuration("First.xctestrun")
        self.fs.configuration("Second.xctestrun")
        self.fs.close_errors = {200: OSError("first-close"), 101: OSError("parent-close")}
        original = self.fs.read
        def first_failure(fd, maximum):
            if fd == 200:
                raise OSError("first-read")
            return original(fd, maximum)
        with patch.object(receipt.os, "read", side_effect=first_failure):
            result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
        self.assertEqual(len(result.captures[0].refusals), 2)
        self.assertIn("first-read", result.captures[0].refusals[0])
        self.assertIn("first-close", result.captures[0].refusals[1])
        self.assertEqual(result.captures[1].data, b"vendor output")
        self.assertIn("parent-close", result.failures[0])
        self.assertEqual(self.fs.closed, [200, 201, 101])

    def testRawNamedReplacementAndParentReplacementRefuse(self):
        name = self.fs.configuration()
        original = self.fs.read
        def replace_after_read(fd, maximum):
            data = original(fd, maximum)
            self.fs.overrides[name] = metadata(999, size=len(self.fs.data[name]))
            self.fs.overrides["Products"] = metadata(9999, stat.S_IFDIR | 0o700)
            return data
        with patch.object(receipt.os, "read", side_effect=replace_after_read):
            result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
        self.assertIsNone(result.captures[0].data)
        self.assertIn("replaced", result.captures[0].refusals[0])
        self.assertIn("directory changed", result.failures[0])

    def testRawDeadlineAndForgedWorkspaceDoNotOpenAnything(self):
        self.fs.now = 900
        result = receipt.capture_configurations(self.fs.workspace(), deadline=900)
        self.assertIn("deadline", result.failures[0])
        with self.assertRaises(pc.Refusal):
            receipt.capture_configurations(SimpleNamespace(), deadline=900)
        self.mocks["open"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
