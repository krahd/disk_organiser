"""Memory-only command/deadline checks; no filesystem or process operations."""
import unittest

import probe_contract as pc
import stage_b_commands as sc


ROOT = '/private/tmp/disk-selection-build-memory'
PRODUCTS = ROOT + '/Products'
XCODE = '/Applications/Xcode_16.4.app/Contents/Developer/usr/bin/xcodebuild'
VERSIONS = (
    (XCODE, '-version'),
    ('/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-version'),
    ('/usr/bin/xcrun', 'swift', '--version'),
)
HOST = PRODUCTS + '/Debug/OwnedFolderProbe.app'
RUNNER = PRODUCTS + '/Debug/SelectionProbeUITests-Runner.app'
TESTS = RUNNER + '/Contents/PlugIns/SelectionProbeUITests.xctest'
BUILD = (
    XCODE, 'build-for-testing', '-project', ROOT + '/Source/Probe.xcodeproj',
    '-scheme', 'OwnedFolderProbe', '-configuration', 'Debug', '-destination', 'platform=macOS',
    '-derivedDataPath', ROOT + '/Derived', 'SYMROOT=' + PRODUCTS, 'OBJROOT=' + ROOT + '/Intermediates',
    'CODE_SIGNING_ALLOWED=NO', 'CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO',
    '-only-testing:SelectionProbeUITests/SelectionProbeUITests/testSelectedReadSucceedsOnlyDuringScope',
    '-only-testing:SelectionProbeUITests/SelectionProbeUITests/testGenuinePanelCancellationRetiresWithoutSelection',
    '-only-testing:SelectionProbeUITests/SelectionProbeUITests/testActiveReadCancelRetiresBeforeRetry',
)
SIGN = ('/usr/bin/codesign', '--force', '--sign', '-', '--timestamp=none')
OBSERVATIONS = VERSIONS + tuple(command for bundle in (HOST, RUNNER, TESTS) for command in (
    ('/usr/bin/codesign', '--verify', '--strict', bundle),
    ('/usr/bin/codesign', '--display', '--verbose=4', bundle),
    ('/usr/bin/codesign', '--display', '--entitlements', '-', '--xml', bundle),
))
COMMANDS = VERSIONS + (BUILD, SIGN + (TESTS,), SIGN + (RUNNER,),
                      SIGN + ('--entitlements', ROOT + '/Source/Host/host.entitlements.inert.plist', HOST)) + OBSERVATIONS * 2
CEILINGS = (20,) * 3 + (600,) + (30,) * 3 + (20,) * 24


class Clock:
    def __init__(self, now=100):
        self.now = now

    def __call__(self):
        return self.now


class StageBCommandTests(unittest.TestCase):
    def guard(self, consumed=0):
        clock = Clock()
        guard = sc.CommandGuard(ROOT, PRODUCTS, 100, clock)
        for index in range(consumed):
            guard.check(COMMANDS[index], CEILINGS[index])
        self.assertEqual(guard.count, consumed)
        return guard, clock

    def assertStopped(self, guard, count):
        with self.assertRaises(pc.Refusal):
            guard.check(COMMANDS[min(count, 30)], 20)
        with self.assertRaises(pc.Refusal):
            guard.complete()
        self.assertEqual(guard.count, count)

    def testAllThirtyOneExactCommandsConsumeOnce(self):
        guard, _ = self.guard()
        self.assertEqual(len(COMMANDS), 31)
        self.assertEqual(sc.COMMAND_COUNT, 31)
        for index, command in enumerate(COMMANDS):
            self.assertEqual(guard.check(command, CEILINGS[index]), CEILINGS[index])
            self.assertEqual(guard.count, index + 1)
        guard.complete()
        self.assertStopped(guard, 31)
        self.assertEqual(guard.remaining_work(), 0)
        self.assertEqual(guard.remaining_finalisation(), 900)

    def testEveryArgumentMutationRefusesAndStops(self):
        for index, command in enumerate(COMMANDS):
            for position in range(len(command)):
                with self.subTest(index=index, position=position):
                    guard, _ = self.guard(index)
                    candidate = command[:position] + (command[position] + '-changed',) + command[position + 1:]
                    with self.assertRaises(pc.Refusal):
                        guard.check(candidate, CEILINGS[index])
                    self.assertStopped(guard, index)

    def testEveryMissingOrExtraArgumentRefuses(self):
        for index, command in enumerate(COMMANDS):
            for position in range(len(command)):
                for candidate in (command[:position] + command[position + 1:],
                                  command[:position] + ('--extra',) + command[position:]):
                    with self.subTest(index=index, position=position, candidate=candidate):
                        guard, _ = self.guard(index)
                        with self.assertRaises(pc.Refusal):
                            guard.check(candidate, CEILINGS[index])
                        self.assertStopped(guard, index)

    def testAllDifferentReorderedCommandsRefuse(self):
        for index, command in enumerate(COMMANDS):
            for other in COMMANDS:
                if other == command:
                    continue  # Identical tuples recur only at their fixed slots.
                with self.subTest(index=index, other=other):
                    guard, _ = self.guard(index)
                    with self.assertRaises(pc.Refusal):
                        guard.check(other, CEILINGS[index])
                    self.assertStopped(guard, index)

    def testEveryDifferentArgumentSwapRefuses(self):
        for index, command in enumerate(COMMANDS):
            for left in range(len(command)):
                for right in range(left + 1, len(command)):
                    if command[left] == command[right]:
                        continue
                    guard, _ = self.guard(index)
                    candidate = list(command)
                    candidate[left], candidate[right] = candidate[right], candidate[left]
                    with self.subTest(index=index, left=left, right=right), self.assertRaises(pc.Refusal):
                        guard.check(tuple(candidate), CEILINGS[index])
                    self.assertStopped(guard, index)

    def testEveryImmediateRepeatRefuses(self):
        for consumed in range(1, 32):
            guard, _ = self.guard(consumed)
            with self.assertRaises(pc.Refusal):
                guard.check(COMMANDS[consumed - 1], CEILINGS[consumed - 1])
            self.assertStopped(guard, consumed)

    def testForbiddenActionsAndShellAlwaysRefuse(self):
        forbidden = ((XCODE, 'test'), (XCODE, 'test-without-building'),
                     ('/usr/bin/open', HOST), (HOST + '/Contents/MacOS/OwnedFolderProbe',),
                     ('/bin/sh', '-c', 'true'), ('/usr/bin/xcrun', 'simctl', 'launch'),
                     ('/usr/bin/codesign', '--force', '--deep', '--sign', '-', HOST))
        for index in range(31):
            for command in forbidden:
                with self.subTest(index=index, command=command):
                    guard, _ = self.guard(index)
                    with self.assertRaises(pc.Refusal):
                        guard.check(command, CEILINGS[index])
                    self.assertStopped(guard, index)

    def testMalformedArgumentsRefuse(self):
        class Text(str):
            pass
        class Arguments(tuple):
            pass
        for arguments in (None, [], list(VERSIONS[0]), ' '.join(VERSIONS[0]), (),
                          (XCODE.encode(), '-version'), (Text(XCODE), '-version'), Arguments(VERSIONS[0])):
            guard, _ = self.guard()
            with self.assertRaises(pc.Refusal):
                guard.check(arguments, 20)
            self.assertStopped(guard, 0)

    def testEveryPrematureCompletionConsumesGuard(self):
        for count in range(31):
            guard, _ = self.guard(count)
            with self.assertRaises(pc.Refusal):
                guard.complete()
            self.assertStopped(guard, count)

    def testStopAfterAnyDownstreamFailurePreservesFinalisation(self):
        for count in range(32):
            guard, clock = self.guard(count)
            guard.stop()
            guard.stop()
            clock.now = 700
            self.assertStopped(guard, count)
            self.assertEqual(guard.remaining_work(), 0)
            self.assertEqual(guard.remaining_finalisation(), 300)

    def testFixedPerCallCeilingsAndSmallerRequests(self):
        for index, ceiling in enumerate(CEILINGS):
            for request in (0.25, 10, ceiling, ceiling + 1, 1000000):
                guard, _ = self.guard(index)
                self.assertEqual(guard.check(COMMANDS[index], request), min(request, ceiling))

    def testInvalidTimeoutsConsumeWithoutAdmission(self):
        for value in (0, -1, True, False, '20', None, float('nan'), float('inf'), -float('inf'), 10 ** 1000):
            guard, _ = self.guard()
            with self.assertRaises(pc.Refusal):
                guard.check(COMMANDS[0], value)
            self.assertStopped(guard, 0)

    def testNineSecondAllowanceBeforeEveryCommand(self):
        for index in range(31):
            for elapsed, expected in ((0, CEILINGS[index]), (700, 11), (710, 1), (710.5, 0.5)):
                with self.subTest(index=index, elapsed=elapsed):
                    guard, clock = self.guard(index)
                    clock.now = 100 + elapsed
                    self.assertEqual(guard.check(COMMANDS[index], CEILINGS[index]), expected)
                    self.assertEqual(guard.count, index + 1)

    def testExhaustionBeforeEveryCommandStopsAdmission(self):
        for index in range(31):
            for elapsed in (711, 719, 720, 721, 899, 900, 901):
                with self.subTest(index=index, elapsed=elapsed):
                    guard, clock = self.guard(index)
                    clock.now = 100 + elapsed
                    with self.assertRaises(pc.Refusal):
                        guard.check(COMMANDS[index], CEILINGS[index])
                    self.assertStopped(guard, index)
                    self.assertEqual(guard.remaining_finalisation(), max(0, 900 - elapsed))

    def testElapsedWorkBetweenCommandsCounts(self):
        guard, clock = self.guard()
        guard.check(COMMANDS[0], 20)
        clock.now += 709
        self.assertEqual(guard.check(COMMANDS[1], 20), 2)
        clock.now += 2
        with self.assertRaises(pc.Refusal):
            guard.check(COMMANDS[2], 20)
        self.assertStopped(guard, 2)

    def testWorkAndFinalisationBoundaries(self):
        guard, clock = self.guard()
        for elapsed, work, finalisation in ((0, 720, 900), (711, 9, 189),
                                            (719.5, 0.5, 180.5), (720, 0, 180),
                                            (899.5, 0, 0.5), (900, 0, 0), (901, 0, 0)):
            clock.now = 100 + elapsed
            self.assertEqual(guard.remaining_work(), work)
            self.assertEqual(guard.remaining_finalisation(), finalisation)
        self.assertStopped(guard, 0)

    def testCompleteChecksDeadlineAndClockAfterFinalCommand(self):
        for elapsed in (711, 719.5):
            guard, clock = self.guard(31)
            clock.now = 100 + elapsed
            guard.complete()
            self.assertEqual(guard.remaining_finalisation(), 900 - elapsed)
        for value in (820, 1000, float('nan'), 99):
            guard, clock = self.guard(31)
            clock.now = value
            with self.assertRaises(pc.Refusal):
                guard.complete()
            self.assertStopped(guard, 31)

    def testInvalidStartAndClockRefuseConstruction(self):
        for started in (None, '100', True, float('nan'), float('inf'), -float('inf'), 10 ** 1000):
            with self.assertRaises(pc.Refusal):
                sc.CommandGuard(ROOT, PRODUCTS, started, Clock())
        with self.assertRaises(pc.Refusal):
            sc.CommandGuard(ROOT, PRODUCTS, 100, 100)

    def testInvalidClockCannotRecoverAfterAnyBudgetOperation(self):
        for method in ('check', 'remaining_work', 'remaining_finalisation', 'complete'):
            for value in (None, '101', True, float('nan'), float('inf'), -float('inf'), 99, 10 ** 1000):
                with self.subTest(method=method, value=value):
                    guard, clock = self.guard(31 if method == 'complete' else 0)
                    clock.now = value
                    with self.assertRaises(pc.Refusal):
                        if method == 'check':
                            guard.check(COMMANDS[0], 20)
                        else:
                            getattr(guard, method)()
                    clock.now = 101
                    self.assertStopped(guard, 31 if method == 'complete' else 0)
                    with self.assertRaises(pc.Refusal):
                        guard.remaining_finalisation()

    def testBackwardsClockBetweenValidSamplesRefuses(self):
        guard, clock = self.guard()
        clock.now = 110
        self.assertEqual(guard.remaining_finalisation(), 890)
        clock.now = 109
        with self.assertRaises(pc.Refusal):
            guard.check(COMMANDS[0], 20)
        self.assertStopped(guard, 0)

    def testOverflowingElapsedClockStops(self):
        clock = Clock(1e308)
        guard = sc.CommandGuard(ROOT, PRODUCTS, -1e308, clock)
        with self.assertRaises(pc.Refusal):
            guard.check(COMMANDS[0], 20)
        self.assertStopped(guard, 0)

    def testClockExceptionStopsAndIsNotRetried(self):
        calls = []
        def broken():
            calls.append(1)
            raise RuntimeError('synthetic clock failure')
        guard = sc.CommandGuard(ROOT, PRODUCTS, 100, broken)
        with self.assertRaises(RuntimeError):
            guard.check(COMMANDS[0], 20)
        self.assertStopped(guard, 0)
        with self.assertRaises(pc.Refusal):
            guard.remaining_finalisation()
        self.assertEqual(calls, [1])

    def testOwnedPathSpellingAndProductsRelationship(self):
        bad = ('/tmp/disk-selection-build-memory', '/private/tmp/disk-selection-owned-memory',
               '/private/tmp/disk-selection-build-', ROOT + '/', ROOT + '/child', ROOT + '/..',
               ROOT + '\\child', ROOT + '\0', ROOT + '\n', ROOT + '-é',
               '/private/tmp/disk-selection-build-' + 'a' * 129, None, ROOT.encode())
        for root in bad:
            with self.subTest(root=root), self.assertRaises(pc.Refusal):
                sc.CommandGuard(root, PRODUCTS, 100, Clock())
        for products in (ROOT, PRODUCTS + '/', PRODUCTS + '/..', PRODUCTS.lower(),
                         ROOT + '/Other', '/private/tmp/disk-selection-build-other/Products', None):
            with self.subTest(products=products), self.assertRaises(pc.Refusal):
                sc.CommandGuard(ROOT, products, 100, Clock())

    def testOtherOwnedRootCannotSubstituteArguments(self):
        other = '/private/tmp/disk-selection-build-other'
        guard = sc.CommandGuard(other, other + '/Products', 100, Clock())
        for command in VERSIONS:
            guard.check(command, 20)
        with self.assertRaises(pc.Refusal):
            guard.check(BUILD, 600)
        self.assertStopped(guard, 3)

    def testExactOwnerPathsRebindOnlyFixedPathPositions(self):
        other = '/private/tmp/disk-selection-build-ab0123_-'
        guard = sc.CommandGuard(other, other + '/Products', 100, Clock())
        for index, command in enumerate(COMMANDS):
            expected = tuple(argument.replace(ROOT, other) for argument in command)
            guard.check(expected, CEILINGS[index])
        guard.complete()
        self.assertEqual(guard.count, 31)


if __name__ == '__main__':
    unittest.main()
