"""Pure, single-attempt Stage B command and cooperative deadline policy.

Paths must come from the parent's retained owners. Their spelling is checked
here; strings never establish ownership or filesystem authority. This module
does no I/O, creates no process, and cannot establish successful tool results.
"""
import math
import re

import probe_contract as pc


XCODE = '/Applications/Xcode_16.4.app/Contents/Developer/usr/bin/xcodebuild'
VERSION_COMMANDS = (
    (XCODE, '-version'),
    ('/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-version'),
    ('/usr/bin/xcrun', 'swift', '--version'),
)
WORK_SECONDS = 720
TOTAL_SECONDS = 900
RETIREMENT_SECONDS = 9
COMMAND_COUNT = 32


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _commands(root, products):
    host = products + '/Debug/OwnedFolderProbe.app'
    runner = products + '/Debug/SelectionProbeUITests-Runner.app'
    tests = runner + '/Contents/PlugIns/SelectionProbeUITests.xctest'
    build = (
        XCODE, 'build-for-testing', '-project', root + '/Source/Probe.xcodeproj',
        '-scheme', 'OwnedFolderProbe', '-configuration', 'Debug',
        '-destination', 'platform=macOS', '-derivedDataPath', root + '/Derived',
        'SYMROOT=' + products, 'OBJROOT=' + root + '/Intermediates',
        'CODE_SIGNING_ALLOWED=NO', 'CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO',
        '-only-testing:SelectionProbeUITests/SelectionProbeUITests/testSelectedReadSucceedsOnlyDuringScope',
        '-only-testing:SelectionProbeUITests/SelectionProbeUITests/testGenuinePanelCancellationRetiresWithoutSelection',
        '-only-testing:SelectionProbeUITests/SelectionProbeUITests/testActiveReadCancelRetiresBeforeRetry',
    )
    sign = ('/usr/bin/codesign', '--force', '--sign', '-', '--timestamp=none')
    versions = tuple((arguments, 20) for arguments in VERSION_COMMANDS)
    signatures = tuple((arguments, 20) for bundle in (host, runner, tests) for arguments in (
        ('/usr/bin/codesign', '--verify', '--strict', bundle),
        ('/usr/bin/codesign', '--display', '--verbose=4', bundle),
        ('/usr/bin/codesign', '--display', '--entitlements', '-', '--xml', bundle),
    ))
    signing = ((sign + (tests,), 30), (sign + (runner,), 30),
               (sign + ('--entitlements', root + '/Source/Host/host.entitlements.inert.plist', host), 30))
    inspector = (('/Applications/Xcode_16.4.app/Contents/Developer/Toolchains/'
                  'XcodeDefault.xctoolchain/usr/bin/otool-classic', '-arch', 'all', '-L',
                  host + '/Contents/MacOS/OwnedFolderProbe'), 20)
    return versions + ((build, 600),) + signing + (inspector,) + (versions + signatures) * 2


class CommandGuard:
    """Admit one exact sequence. The parent must stop() after downstream failure."""

    def __init__(self, workspace_path, products_path, started_at, clock):
        pc.require(type(workspace_path) is str and
                   re.fullmatch(r'/private/tmp/disk-selection-build-[A-Za-z0-9_-]{1,128}', workspace_path),
                   'Stage B fixed owned workspace spelling')
        pc.require(type(products_path) is str and products_path == workspace_path + '/Products',
                   'Stage B fixed owned products relationship')
        pc.require(_finite(started_at) and callable(clock), 'Stage B monotonic clock required')
        self._commands = _commands(workspace_path, products_path)
        self._started = self._last = started_at
        self._clock = clock
        self._next = 0
        self._stopped = self._clock_failed = False

    @property
    def count(self):
        """Number admitted, not number executed successfully."""
        return self._next

    def stop(self):
        self._stopped = True

    def _elapsed(self):
        pc.require(not self._clock_failed, 'Stage B clock already failed')
        try:
            now = self._clock()
            pc.require(_finite(now) and now >= self._last, 'Stage B nonfinite or backwards clock')
            elapsed = now - self._started
            pc.require(_finite(elapsed), 'Stage B elapsed clock range')
            self._last = now
            if elapsed >= WORK_SECONDS:
                self.stop()
            return elapsed
        except BaseException:
            self._clock_failed = True
            self.stop()
            raise

    def remaining_work(self):
        elapsed = self._elapsed()
        return 0 if self._stopped else max(0, WORK_SECONDS - elapsed)

    def remaining_finalisation(self):
        # Independent evidence and retirement still need their budget after stop.
        return max(0, TOTAL_SECONDS - self._elapsed())

    def check(self, arguments, requested_timeout):
        try:
            pc.require(not self._stopped and self._next < COMMAND_COUNT, 'Stage B command sequence consumed')
            expected, ceiling = self._commands[self._next]
            pc.require(type(arguments) is tuple and len(arguments) == len(expected) and
                       all(type(value) is str for value in arguments) and arguments == expected,
                       'Stage B exact ordered command required')
            pc.require(_finite(requested_timeout) and requested_timeout > 0, 'Stage B positive finite timeout required')
            timeout = min(requested_timeout, ceiling, self.remaining_work() - RETIREMENT_SECONDS)
            pc.require(timeout > 0, 'Stage B work deadline or retirement allowance exhausted')
            self._next += 1
            return timeout
        except BaseException:
            self.stop()
            raise

    def complete(self):
        """Require every admission within the work budget, then retire admission."""
        try:
            pc.require(self.remaining_work() > 0 and self._next == COMMAND_COUNT,
                       'Stage B command sequence incomplete or consumed')
        finally:
            self.stop()


if __name__ == '__main__':
    raise SystemExit(2)
