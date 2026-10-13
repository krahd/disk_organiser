"""Bounded direct-child owner. Imported only by the closed-default controller.

No shell, process-name kill, inherited source FD or ambient environment. This
module's entry refuses; Stage-A tests mock every process/pipe/time operation.
"""
from dataclasses import dataclass
import errno
import os
import selectors
import signal
import subprocess
import time

import probe_contract as pc

MAX_OUTPUT = 8 * 1024 * 1024
TOOLS = {"/usr/bin/codesign", "/usr/bin/xcrun", "/Applications/Xcode_16.4.app/Contents/Developer/usr/bin/xcodebuild",
         "/Applications/Xcode_16.4.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/otool-classic"}

@dataclass(frozen=True)
class ProcessResult:
    arguments: tuple[str, ...]
    stdout: bytes
    stderr: bytes
    returncode: int | None
    direct_child_reaped: bool
    cancelled: bool
    reason: str
    owned_group_retired: bool = False

class ProcessFailure(pc.Refusal):
    def __init__(self, result):
        self.result = result
        super().__init__(result.reason)


def _retire(child, *, seconds=3):
    """Only the retained direct child; never kill an unverified descendant PID."""
    deadline = time.monotonic() + seconds
    if child.poll() is None:
        try:
            child.terminate()
        except ProcessLookupError:
            pass
    while child.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    if child.poll() is None:
        try:
            child.kill()
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + seconds
    while child.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    # poll() reaps the retained Popen child. A signal alone is never proof.
    return child.returncode is not None


def _group_retired(pid, *, seconds=3):
    # start_new_session makes the retained direct child's PID its group ID.
    # Only observe this group. Never kill after its leader has been reaped:
    # a reused numeric group can cause a conservative refusal, not a signal.
    pc.require(type(pid) is int and 1 < pid < 2**31, "owned process group identity")
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            os.killpg(pid, 0)
        except OSError as error:
            if error.errno == errno.ESRCH:
                return True
            return False
        time.sleep(0.02)
    return False


def run(arguments, *, cwd, environment, timeout, cancelled=lambda: False, max_output=MAX_OUTPUT):
    pc.require(type(arguments) is tuple and arguments and arguments[0] in TOOLS,
               "fixed native tool required")
    pc.require(all(type(x) is str and 0 < len(x.encode()) <= 4096 and '\0' not in x for x in arguments), "tool arguments")
    pc.require(type(environment) is dict and 0 < timeout <= 900 and 0 < max_output <= MAX_OUTPUT, "tool bounds")
    pc.require(type(cwd) is str and cwd.startswith('/private/tmp/disk-selection-build-'), "owned tool cwd")
    if cancelled():
        raise ProcessFailure(ProcessResult(arguments, b'', b'', None, True, True, 'cancelled-before-start', True))
    child = None; selector = None; streams = []; captured = {"stdout": bytearray(), "stderr": bytearray()}
    reason = ''; was_cancelled = False; reaped = True; group_retired = False
    try:
        child = subprocess.Popen(arguments, cwd=cwd, env=dict(environment), stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
                                 start_new_session=True, shell=False)
        # Register both owned pipes before any operation on either can fail.
        streams = [child.stdout, child.stderr]
        pc.require(all(stream is not None for stream in streams), "missing owned pipe")
        selector = selectors.DefaultSelector()
        for name, stream in zip(("stdout", "stderr"), streams):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        deadline = time.monotonic() + timeout
        while selector.get_map() or child.poll() is None:
            if cancelled():
                was_cancelled = True; reason = 'cancelled'; break
            if time.monotonic() >= deadline:
                reason = 'tool-deadline'; break
            for key, _ in selector.select(0.05):
                try:
                    data = os.read(key.fileobj.fileno(), 4096)
                except (InterruptedError, BlockingIOError):
                    continue
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                remaining = max_output - sum(map(len, captured.values()))
                captured[key.data].extend(data[:remaining])
                if len(data) > remaining:
                    reason = 'tool-output-overflow'; break
            if reason:
                break
        if not reason and child.returncode != 0:
            reason = 'tool-exit'
    except BaseException as error:
        reason = reason or 'tool-owner-error:' + type(error).__name__
        if child is None:
            reaped = False  # A failed spawn handoff is never retirement proof.
    finally:
        if child is not None:
            try:
                reaped = _retire(child)
            except BaseException:
                reaped = False
            if not reaped:
                reason = 'direct-child-retirement-unproved'
            try:
                group_retired = _group_retired(child.pid)
            except BaseException:
                group_retired = False
            if not group_retired and reaped:
                reason = 'owned-process-group-retirement-unproved'
        # Cleanup attempts every owned pipe even if another close fails.
        for stream in streams:
            if stream is not None:
                try:
                    stream.close()
                except BaseException:
                    reason = 'pipe-retirement-unproved'
        if selector is not None:
            try:
                selector.close()
            except BaseException:
                reason = 'selector-retirement-unproved'
    result = ProcessResult(arguments, bytes(captured['stdout']), bytes(captured['stderr']),
                           child.returncode if child is not None else None, reaped, was_cancelled, reason, group_retired)
    if reason:
        raise ProcessFailure(result)
    return result


def prove_retired(processes, *, timeout=5):
    """Observe supplied owned-runner/host PIDs; never signal them to terminate.

    The caller must bind these PIDs to the just-observed native receipt. PID
    reuse can cause a conservative refusal, never a kill of another process.
    """
    pc.require(type(processes) is tuple and 0 < len(processes) <= 8 and
               all(type(pid) is int and 1 < pid < 2**31 for pid in processes), "owned PID set")
    deadline = time.monotonic() + timeout
    remaining = set(processes)
    while remaining and time.monotonic() < deadline:
        for pid in tuple(remaining):
            try:
                os.kill(pid, 0)
            except OSError as error:
                if error.errno == errno.ESRCH:
                    remaining.remove(pid)
                else:
                    raise pc.Refusal('process-retirement-inconclusive') from error
        if remaining:
            time.sleep(0.02)
    pc.require(not remaining, 'owned-service-process-still-present')
    return tuple(sorted(processes))


if __name__ == '__main__':
    raise SystemExit(2)
