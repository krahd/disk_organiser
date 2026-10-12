"""Single-use, same-thread build admission. It cannot enable Stage C.

This is lifecycle ownership, not OS isolation or consent. Only the disabled
fixed driver issues it. Imported metadata is never an admission constructor.
"""
import math
import threading
import time
import weakref

import probe_contract as pc
import stage_b_profile as profile
from stage_b_commands import CommandGuard

_KEY = object()


class Admission:
    def __init__(self, key, started_at, clock):
        pc.require(key is _KEY and profile.BUILD_ONLY_ENABLED is True, 'build-only profile disabled')
        pc.require(type(started_at) in (int, float) and math.isfinite(started_at), 'driver clock')
        self.thread = threading.get_ident()
        self.started_at, self.clock = started_at, clock
        self.last_clock = started_at
        self.state, self.owner, self.guard = 'issued', None, None

    def _thread(self):
        pc.require(threading.get_ident() == self.thread, 'admission owner thread')

    def consume(self, source_commit, rows):
        self._thread()
        pc.require(profile.BUILD_ONLY_ENABLED is True and self.state == 'issued', 'spent build admission')
        self.state = 'consumed'
        pc.require(source_commit == profile.HOST_SOURCE_COMMIT and rows == profile.HOST_ROWS,
                   'admission source identity')
        self.work_check()

    def work_check(self):
        self._thread()
        pc.require(self.state in ('consumed', 'prepared', 'running'), 'admission work inactive')
        now = self.clock()
        pc.require(type(now) in (int, float) and math.isfinite(now) and
                   self.last_clock <= now < self.started_at + 720, 'admission work deadline')
        self.last_clock = now
        return False

    def attach(self, owner):
        self._thread()
        pc.require(self.state == 'consumed' and self.owner is None, 'admission already owned')
        self.guard = CommandGuard(owner.workspace.path, owner.workspace.products_path, self.started_at, self.clock)
        self.owner = weakref.ref(owner)
        self.state = 'prepared'

    def begin(self, owner):
        self._thread()
        pc.require(profile.BUILD_ONLY_ENABLED is True and self.state == 'prepared' and
                   self.owner is not None and self.owner() is owner, 'build admission owner')
        self.state = 'running'

    def before_tool(self, owner, arguments, timeout):
        self._thread()
        pc.require(self.state == 'running' and self.owner() is owner, 'build admission inactive')
        return self.guard.check(arguments, timeout)

    def complete(self, owner):
        self._thread()
        pc.require(self.state == 'running' and self.owner() is owner, 'build admission inactive')
        self.guard.complete()
        self.state = 'complete'

    def stop(self):
        self._thread()
        if self.guard is not None:
            self.guard.stop()
        self.state = 'stopped'

    def retire(self):
        self.stop()
        self.owner = None
        self.state = 'retired'


def _issue(started_at, clock=time.monotonic):
    return Admission(_KEY, started_at, clock)
