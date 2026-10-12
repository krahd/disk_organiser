"""Closed-default Stage B/C owner. No CLI or workflow invokes this source.

Both gate functions deliberately return False. Changing either requires its
separate reviewed authority decision. Stage-A tests patch gates and ALL process,
fixture, workspace and filesystem operations with memory-only doubles.
"""
from dataclasses import dataclass, replace, fields, is_dataclass
import hashlib
import json
import os
import re
import stat
import threading

import bounded_process as bp
import fixture_inputs as fi
import native_observations as no
import owned_build_observation as ob
import probe_contract as pc
import xctestrun_binding as xb
import runner_expectations as rx
import stage_b_admission as ba

TOTAL_LOG_BYTES = 32 * 1024 * 1024
SOURCE_LIMIT = 2 * 1024 * 1024
_CONTROLLER_KEY = object()
REVIEWED_SOURCE_COMMIT = "UNREVIEWED"
REVIEWED_SOURCE_MANIFEST_SHA256 = "UNREVIEWED"


def _stage_b_approved():
    return False


def _stage_c_approved():
    return False


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def _sha(value):
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class Inspection:
    freeze: ob.FrozenBuild
    observations: no.Observations
    fixture_digest: str
    source_commit: str
    source_rows: tuple[tuple[str, str], ...]
    generated_rows: tuple[tuple[str, str], ...]
    configuration_name: str
    context: bytes
    preparation_log_digests: tuple[str, ...]
    runner_binding: rx.Derivation


@dataclass(frozen=True)
class RuntimeReceipt:
    source_commit: str
    case_id: str
    inspection_digest: str
    raw_stdout: bytes
    raw_stderr: bytes
    methods: tuple[str, ...]
    capture_names: tuple[str, ...]
    observed_retired_pids: tuple[int, ...]
    original_result_inventory: tuple[str, ...]
    original_capture_inventory: tuple[str, ...]


def _canonical(value):
    """Versioned, type-tagged fingerprint input; never an ownership loader."""
    if is_dataclass(value) and not isinstance(value, type):
        return ['dataclass', type(value).__module__, type(value).__qualname__,
                [[field.name, _canonical(getattr(value, field.name))] for field in fields(value)]]
    if type(value) is bytes:
        return ['bytes', value.hex()]
    if type(value) in (str, int, bool):
        return [type(value).__name__, value]
    if type(value) is tuple:
        return ['tuple', [_canonical(item) for item in value]]
    raise pc.Refusal('unsupported inspection fingerprint member')


def inspection_digest(inspection):
    pc.require(type(inspection) is Inspection, 'complete inspection required')
    return _sha(_json(['owned-probe-inspection-v1', _canonical(inspection)]))


def _write_bound_configuration(workspace, binding, *, check=None):
    """One new fixed leaf, never overwrite the emitted configuration."""
    pc.require(type(binding) is rx.Derivation and binding.derived_name == rx.DERIVED_NAME,
               'fixed derived configuration')
    ob._check(check)
    options = ob._check_options(check)
    data = binding.derived.raw
    rx.verify(binding, workspace.read_configuration(binding.original_name, **options), data, dict(binding.expectations))
    with ob._Descriptors(check=check) as ledger:
        parent = workspace._products(ledger)
        fd = ledger.acquire(lambda: os.open(rx.DERIVED_NAME, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                            os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, 0o600, dir_fd=parent))
        initial = os.fstat(fd)
        pc.require(stat.S_ISREG(initial.st_mode) and initial.st_nlink == 1 and initial.st_uid == os.getuid() and
                   stat.S_IMODE(initial.st_mode) == 0o600 and initial.st_size == 0, 'fresh bound configuration')
        offset = 0
        for _ in range(4096):
            ob._check(check)
            if offset == len(data):
                break
            try:
                amount = os.write(fd, data[offset:])
            except InterruptedError:
                continue
            ob._check(check)
            pc.require(amount > 0, 'bound configuration write progress'); offset += amount
        pc.require(offset == len(data), 'bound configuration write budget')
        ob._check(check)
        os.fsync(fd)
        ob._check(check)
        final = os.fstat(fd)
        named = os.stat(rx.DERIVED_NAME, dir_fd=parent, follow_symlinks=False)
        pc.require((initial.st_dev, initial.st_ino) == (final.st_dev, final.st_ino) == (named.st_dev, named.st_ino) and
                   stat.S_ISREG(final.st_mode) and final.st_uid == initial.st_uid and final.st_nlink == 1 and
                   stat.S_IMODE(final.st_mode) == 0o600 and final.st_size == len(data), 'bound configuration changed')
    ob._check(check)
    rx.verify(binding, workspace.read_configuration(binding.original_name, **options),
              workspace.read_configuration(rx.DERIVED_NAME, **options), dict(binding.expectations))
    ob._check(check)


def _relative(path):
    pc.require(type(path) is str and 0 < len(path.encode()) <= 1024 and re.fullmatch(r'[A-Za-z0-9_./-]+', path) and
               all(x not in ('', '.', '..') for x in path.split('/')), 'source relative path')
    return path.split('/')


def _source_files(files):
    pc.require(type(files) is dict and 1 <= len(files) <= 48 and
               sum(len(v) for v in files.values() if type(v) is bytes) <= SOURCE_LIMIT, 'source pack budget')
    for path, data in files.items():
        parts = _relative(path)
        pc.require(parts[0] in ('Host', 'UITests', 'Generated', 'Probe.xcodeproj') and
                   type(data) is bytes and 0 < len(data) <= 262144, 'source pack member')
    required = {'Probe.xcodeproj/project.pbxproj', 'Probe.xcodeproj/xcshareddata/xcschemes/OwnedFolderProbe.xcscheme',
                'Host/main.swift', 'Host/host.entitlements.inert.plist', 'Generated/ProbeSeal.swift',
                'Generated/fixture.json', 'Generated/ProbeBuild.xcconfig', 'UITests/SelectionProbeUITests.swift'}
    pc.require(required <= set(files), 'incomplete reviewed source pack')
    return tuple(sorted((p, _sha(b)) for p, b in files.items()))


def _write_inputs(workspace, files, *, cancelled=lambda: False, check=None):
    """Exclusive writes only beneath the retained fresh root; no overwrite."""
    ob._check(check)
    workspace._admit()
    ob._check(check)
    with ob._Descriptors(check=check) as ledger:
        os.mkdir('Source', 0o700, dir_fd=workspace._descriptor)
        source = ledger.acquire(lambda: os.open('Source', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                                dir_fd=workspace._descriptor))
        made = {()}
        for path, data in sorted(files.items()):
            ob._check(check)
            pc.require(not cancelled(), 'source write cancelled')
            parts = _relative(path); parent = source
            for index, part in enumerate(parts[:-1]):
                ob._check(check)
                key = tuple(parts[:index + 1])
                if key not in made:
                    os.mkdir(part, 0o700, dir_fd=parent); made.add(key)
                parent = ledger.acquire(lambda: os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                                        dir_fd=parent))
            fd = ledger.acquire(lambda: os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW |
                                                os.O_NONBLOCK | os.O_CLOEXEC, 0o600, dir_fd=parent))
            used = 0
            for _ in range(4096):
                ob._check(check)
                if used == len(data):
                    break
                pc.require(not cancelled(), 'source write cancelled')
                try:
                    count = os.write(fd, data[used:])
                except InterruptedError:
                    continue
                ob._check(check)
                pc.require(count > 0, 'source write progress'); used += count
            pc.require(used == len(data), 'source write-attempt budget')
            ob._check(check)
            os.fsync(fd)
        for name in ('Home', 'Temp'):
            ob._check(check)
            os.mkdir(name, 0o700, dir_fd=workspace._descriptor)
        ob._check(check)


def _verify_inputs(workspace, expected, *, retain=False, check=None):
    ob._check(check)
    workspace._admit()
    ob._check(check)
    retained = {}
    for path, digest in expected:
        ob._check(check)
        with ob._Descriptors(check=check) as ledger:
            parent = workspace._descriptor
            for part in ['Source'] + _relative(path)[:-1]:
                ob._check(check)
                parent = ledger.acquire(lambda: os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                                        dir_fd=parent))
            fd = ledger.acquire(lambda: os.open(_relative(path)[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                                                dir_fd=parent))
            before = os.fstat(fd)
            pc.require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_uid == os.getuid() and
                       0 < before.st_size <= 262144, 'source observation shape')
            data = bytearray()
            for _ in range(4096):
                ob._check(check)
                try:
                    part = os.read(fd, min(65536, before.st_size + 1 - len(data)))
                except InterruptedError:
                    continue
                ob._check(check)
                if not part:
                    break
                data.extend(part)
                pc.require(len(data) <= before.st_size, 'source observation grew')
            pc.require(len(data) == before.st_size and _sha(data) == digest and
                       ob._stamp(before) == ob._stamp(os.fstat(fd)), 'source input changed')
            if retain:
                retained[path] = bytes(data)
    ob._check(check)
    workspace._admit()
    ob._check(check)
    return retained if retain else None


class PreparationFailure(pc.Refusal):
    def __init__(self, original, dispositions, cleanup_failures=()):
        self.original = original
        self.dispositions = dispositions
        self.cleanup_failures = tuple(cleanup_failures[:256])
        self.omitted_cleanup_failure_count = max(0, len(cleanup_failures) - 256)
        self.failures = tuple(json.dumps(row, sort_keys=True) for row in self.cleanup_failures)
        super().__init__('preparation failed:' + type(original).__name__)


class Experiment:
    def __init__(self, key, workspace, fixture, source_commit, source_rows, generated_rows, input_rows):
        pc.require(key is _CONTROLLER_KEY, 'fresh experiment owner required')
        self.workspace, self.fixture = workspace, fixture
        self.source_commit, self.source_rows = source_commit, source_rows
        self.generated_rows, self.input_rows = generated_rows, input_rows
        self.trace = []; self.inspection = None; self.state = 'prepared'; self.failure = None
        self._active_cancel = lambda: False
        self.failure_evidence = {}
        self._owner_thread = threading.get_ident()
        self._build_admission = None
        self.close_outcomes = {}
        self.environment = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'DEVELOPER_DIR': no.DEVELOPER,
                            'HOME': workspace.path + '/Home', 'TMPDIR': workspace.path + '/Temp',
                            'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8'}

    @classmethod
    def prepare(cls, source_commit, reviewed_files, *, admission=None):
        pc.require((admission is None and _stage_b_approved()) or type(admission) is ba.Admission,
                   'Stage B closed')  # Before any filesystem/tool operation.
        pc.require(type(source_commit) is str and re.fullmatch(r'[0-9a-f]{40}', source_commit), 'source commit')
        source_rows = _source_files(reviewed_files)
        if admission is None:
            pc.require(source_commit == REVIEWED_SOURCE_COMMIT and
                       _sha(_json(list(source_rows))) == REVIEWED_SOURCE_MANIFEST_SHA256,
                       'separately reviewed source identity required')
        else:
            admission.consume(source_commit, source_rows)
        workspace = fixture = None
        check = None if admission is None else admission.work_check
        options = ob._check_options(check)
        try:
            ob._check(check)
            workspace = ob.OwnedBuild.create(**options)
            workspace.create_products_directory(**options)
            capture_identity = workspace.create_captures_directory(**options)
            ob._check(check)
            fixture = fi.create_owned_fixture(**options)
            ob._check(check)
            generated = fi.render_claimed_inputs(fixture.claim, source_commit, workspace.products_path + '/' + no.EXECUTABLES[0], capture_identity)
            ob._check(check)
            files = dict(reviewed_files); files.update(generated)
            _write_inputs(workspace, files, **options)
            ob._check(check)
            result = cls(_CONTROLLER_KEY, workspace, fixture, source_commit, source_rows,
                         tuple(sorted((p, _sha(b)) for p, b in generated.items())),
                         tuple(sorted((p, _sha(b)) for p, b in files.items())))
            if admission is not None:
                admission.attach(result)
                result._build_admission = admission
            return result
        except BaseException as original:
            errors = []
            cleanup_failures = []
            dispositions = {}
            for label, owner in (('fixture', fixture), ('workspace', workspace)):
                if owner is not None:
                    try:
                        owner.close()
                        dispositions[label] = 'closed'
                    except BaseException as error:
                        errors.append(type(error).__name__)
                        cleanup_failures.append(dict(owner=label, **ob._error_record(error)))
                        cleanup_failures.extend(getattr(error, 'cleanup_failures', ()))
                        dispositions[label] = 'unproved:' + type(error).__name__
                else:
                    dispositions[label] = 'not-acquired'
            if admission is not None:
                try:
                    admission.retire()
                except BaseException as error:
                    dispositions['admission'] = 'unproved:' + type(error).__name__
                    cleanup_failures.append(dict(owner='admission', **ob._error_record(error)))
                raise PreparationFailure(original, dispositions, cleanup_failures) from original
            if errors:
                raise ob.RetirementFailure('preparation retirement unproved:' + ','.join(errors),
                                           original, cleanup_failures) from original
            raise

    def _work_options(self):
        return ob._check_options(None if self._build_admission is None else self._build_admission.work_check)

    def _finalisation_check(self):
        if self._build_admission is not None:
            pc.require(self._build_admission.guard.remaining_finalisation() > 0, 'failure disposition deadline')

    def _tool(self, arguments, *, timeout, max_output=bp.MAX_OUTPUT, cancelled=None):
        remaining = TOTAL_LOG_BYTES - sum(len(x.stdout) + len(x.stderr) for x in self.trace)
        pc.require(remaining > 0 and len(self.trace) < 64, 'experiment tool budget')
        if self._build_admission is not None:
            timeout = self._build_admission.before_tool(self, arguments, timeout)
        try:
            result = bp.run(arguments, cwd=self.workspace.path, environment=self.environment,
                            timeout=timeout, max_output=min(remaining, max_output),
                            cancelled=self._active_cancel if cancelled is None else cancelled)
        except bp.ProcessFailure as error:
            self.trace.append(error.result)
            if self._build_admission is not None:
                self._build_admission.stop()
            raise
        self.trace.append(result)
        return result

    def _context(self, observations, configuration_name):
        fixture = pc.decode_claim(self.fixture.claim, pc.FIXTURE_BYTES)
        host = observations.signatures[0]
        return _json({'schemaVersion': 1, 'sourceCommit': self.source_commit, 'fixtureSHA256': _sha(self.fixture.claim),
                      'fixtureRunID': fixture['runID'], 'fixtureCaseID': fixture['caseID'],
                      'buildRoot': self.workspace.path, 'productsRoot': self.workspace.products_path,
                      'workingDirectory': self.workspace.path, 'executable': no.XCODE,
                      'arguments': ['test-without-building', '-xctestrun', self.workspace.products_path + '/' + configuration_name,
                                    '-destination', 'platform=macOS', '-parallel-testing-enabled', 'NO',
                                    '-resultBundlePath', self.workspace.path + '/Results.xcresult'],
                      'environment': self.environment, 'toolchain': dict(observations.toolchain),
                      'observedHostSignature': {'identifier': host.identifier, 'executable': host.executable,
                                                'cdhash': host.cdhash, 'entitlements': dict(host.entitlements), 'valid': True}})

    def inspect_b(self, *, cancelled=lambda: False):
        pc.require(threading.get_ident() == self._owner_thread, "single experiment owner thread")
        pc.require(self.state == 'prepared', 'Stage B unavailable or consumed')
        if self._build_admission is None:
            pc.require(_stage_b_approved(), 'Stage B unavailable or consumed')
        else:
            self._build_admission.begin(self)
        self.state = 'preparing'
        self._active_cancel = cancelled
        try:
            options = self._work_options()
            self.fixture.verify(**options); _verify_inputs(self.workspace, self.input_rows, **options)
            if self._build_admission is not None:
                no.collect_toolchain(self._tool)
            root = self.workspace.path
            build = (no.XCODE, 'build-for-testing', '-project', root + '/Source/Probe.xcodeproj',
                     '-scheme', 'OwnedFolderProbe', '-configuration', 'Debug', '-destination', 'platform=macOS',
                     '-derivedDataPath', root + '/Derived', 'SYMROOT=' + self.workspace.products_path,
                     'OBJROOT=' + root + '/Intermediates', 'CODE_SIGNING_ALLOWED=NO', 'CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO')
            build += tuple('-only-testing:SelectionProbeUITests/' + name for name in xb.METHODS)
            self._tool(build, timeout=600)
            # Sign inner test bundle before its containing runner; host separately.
            for index in (2, 1, 0):
                command = ('/usr/bin/codesign', '--force', '--sign', '-', '--timestamp=none')
                if index == 0:
                    command += ('--entitlements', root + '/Source/Host/host.entitlements.inert.plist')
                self._tool(command + (self.workspace.products_path + '/' + no.PRODUCTS[index],), timeout=30, max_output=65536)
            configuration = self._configuration_name()
            binding = self._prepare_runner_binding(configuration)
            inspection = self._observe(binding.derived_name, binding)
            inspection = replace(inspection, preparation_log_digests=tuple(
                _sha(_json(list(item.arguments)) + b'\0' + item.stdout + b'\0' + item.stderr) for item in self.trace))
            if self._build_admission is not None:
                self._build_admission.complete(self)
            self.inspection = inspection; self.state = 'inspected'; self._active_cancel = lambda: False
            return inspection
        except BaseException as error:
            self.state = 'failed'; self.failure = type(error).__name__; self._active_cancel = lambda: False
            if self._build_admission is not None:
                self._build_admission.stop()
            self._record_b_failure(error)
            raise

    def _configuration_name(self):
        check = self._work_options().get("check")
        ob._check(check)
        names = []
        with ob._Descriptors(check=check) as ledger:
            fd = self.workspace._products(ledger)
            with ob._scan_entries(fd, check=check) as entries:
                entries = iter(entries)
                for index in range(65):
                    ob._check(check)
                    try:
                        entry = next(entries)
                    except StopIteration:
                        break
                    ob._check(check)
                    pc.require(index < 64, 'configuration enumeration budget')
                    if entry.name.endswith('.xctestrun'):
                        names.append(entry.name)
        ob._check(check)
        pc.require(len(names) == 1, 'one observed xctestrun required')
        return names[0]

    def _expectations(self, observations):
        fixture = pc.decode_claim(self.fixture.claim, pc.FIXTURE_BYTES)
        host = observations.signatures[0]
        return dict(zip((rx.PREFIX + key for key in rx.FIELDS),
                        (host.cdhash, host.identifier, host.executable, self.source_commit,
                         _sha(self.fixture.claim), fixture['runID'], fixture['caseID'])))

    def _prepare_runner_binding(self, original_name):
        options = self._work_options()
        ob._check(options.get('check'))
        case = pc.decode_claim(self.fixture.claim, pc.FIXTURE_BYTES)['caseID']
        observed = no.collect(self._tool, self.workspace.products_path, case)
        binding = rx.derive(original_name, self.workspace.read_configuration(original_name, **options), self._expectations(observed))
        _write_bound_configuration(self.workspace, binding, **options)
        return binding

    def _record_b_failure(self, error):
        # B has no accepted FrozenBuild yet. Record partial bounded disposition,
        # attempting every independent check even when a preceding one fails.
        self.failure_evidence['stage'] = 'B'
        self.failure_evidence['original_failure'] = type(error).__name__
        self.failure_evidence['tool_results'] = tuple(self.trace)
        if isinstance(error, bp.ProcessFailure) and not any(item is error.result for item in self.trace):
            self.failure_evidence['untraced_failure_result'] = error.result
        options = ob._check_options(None if self._build_admission is None else self._finalisation_check)
        checks = (('fixture', lambda: self.fixture.verify(**options)),
                  ('source', lambda: _verify_inputs(self.workspace, self.input_rows, **options)),
                  ('partial_products', lambda: self.workspace.inventory(**options)),
                  ('partial_captures', lambda: self.workspace.inventory(captures=True, **options)))
        for label, check in checks:
            try:
                ob._check(options.get('check'))
                result = check()
                self.failure_evidence[label] = result if label.startswith('partial_') else 'unchanged'
            except BaseException as failure:
                self.failure_evidence[label] = 'unproved:' + type(failure).__name__
        # No signing retry, fixture repair, deletion or invented retirement.

    def _observe(self, configuration_name, binding):
        pc.require(type(binding) is rx.Derivation and configuration_name == binding.derived_name,
                   'fixed bound runtime configuration')
        options = self._work_options()
        self.fixture.verify(**options); _verify_inputs(self.workspace, self.input_rows, **options)
        case = pc.decode_claim(self.fixture.claim, pc.FIXTURE_BYTES)['caseID']
        observed = no.collect(self._tool, self.workspace.products_path, case)
        context = self._context(observed, configuration_name)
        frozen = ob.freeze(self.workspace, configuration_name, no.PRODUCTS, context, **options)
        rx.verify(binding, self.workspace.read_configuration(binding.original_name, **options), frozen.raw_configuration,
                  self._expectations(observed))
        rows = {json.loads(row)['path']: json.loads(row) for row in frozen.inventory}
        for path in no.EXECUTABLES:
            pc.require(path in rows and rows[path]['kind'] == 'file' and rows[path]['size'] > 0,
                       'observed executable row required')
        resource = no.PRODUCTS[0] + '/Contents/Resources/fixture.json'
        pc.require(resource in rows and rows[resource]['kind'] == 'file' and
                   rows[resource]['sha256'] == _sha(self.fixture.claim), 'observed fixture resource mismatch')
        self.fixture.verify(**options); _verify_inputs(self.workspace, self.input_rows, **options)
        return Inspection(frozen, observed, _sha(self.fixture.claim), self.source_commit, self.source_rows,
                          self.generated_rows, configuration_name, context, (), binding)

    def run_c(self, reviewed_inspection, *, cancelled=lambda: False):
        pc.require(threading.get_ident() == self._owner_thread, "single experiment owner thread")
        pc.require(_stage_c_approved(), 'Stage C closed')
        pc.require(self.state == 'inspected' and reviewed_inspection is self.inspection,
                   'retained exact inspection required')
        self.state = 'running'  # One attempt; failure cannot retry on stale approval.
        self._active_cancel = cancelled
        result = None; errors = []
        try:
            fresh = self._observe(reviewed_inspection.configuration_name, reviewed_inspection.runner_binding)
            pc.require(replace(fresh, preparation_log_digests=reviewed_inspection.preparation_log_digests) == reviewed_inspection, 'inspection changed before runtime')
            context = pc.decode_claim(reviewed_inspection.context, 65536)
            result = self._tool((context['executable'], *context['arguments']), timeout=900, cancelled=cancelled)
            cases, captures, pids = verify_execution_output(result, reviewed_inspection, self.fixture.claim)
            retired = bp.prove_retired(pids)
            pc.require(replace(self._observe(reviewed_inspection.configuration_name, reviewed_inspection.runner_binding), preparation_log_digests=reviewed_inspection.preparation_log_digests) == reviewed_inspection,
                       'inspection changed after runtime')
            inventory = self.workspace.inventory(results=True)
            pc.require(any(json.loads(row)['kind'] == 'file' for row in inventory), 'original result bundle missing')
            capture_inventory = self.workspace.inventory(captures=True)
            verify_capture_inventory(capture_inventory, result.stdout + b'\n' + result.stderr)
            self.state = 'retired'; self._active_cancel = lambda: False
            return RuntimeReceipt(self.source_commit, pc.decode_claim(self.fixture.claim, pc.FIXTURE_BYTES)['caseID'],
                                  inspection_digest(reviewed_inspection),
                                  result.stdout, result.stderr, cases, captures, retired, inventory, capture_inventory)
        except BaseException as error:
            self.state = 'failed'; self.failure = type(error).__name__; self._active_cancel = lambda: False
            if isinstance(error, bp.ProcessFailure):
                result = error.result
            # Preserve all bounded partial raw output and result files. Never
            # claim success from cleanup, retry the experiment or kill a name/PID.
            if result is not None:
                try:
                    pids = observed_process_ids(result.stdout + b'\n' + result.stderr, self.fixture.claim, self.source_commit)
                    if pids:
                        bp.prove_retired(pids)
                    else:
                        errors.append('no-complete-owned-process-observation')
                except BaseException as cleanup:
                    errors.append(type(cleanup).__name__)
            for label, check in (('fixture', lambda: self.fixture.verify()),
                                 ('source', lambda: _verify_inputs(self.workspace, self.input_rows)),
                                 ('products', lambda: ob.verify_unchanged(self.workspace, reviewed_inspection.freeze,
                                                                        reviewed_inspection.configuration_name, reviewed_inspection.context))):
                try:
                    check(); self.failure_evidence[label] = 'unchanged'
                except BaseException as failure:
                    errors.append(label + ':' + type(failure).__name__)
                    self.failure_evidence[label] = 'unproved:' + type(failure).__name__
            if result is not None:
                for label, options in (('results', {'results': True}), ('captures', {'captures': True})):
                    try:
                        self.failure_evidence[label] = self.workspace.inventory(**options)
                    except BaseException as failure:
                        self.failure_evidence[label] = 'unproved:' + type(failure).__name__
            self.failure += ':' + ','.join(errors)
            raise

    def __del__(self):
        if getattr(self, 'state', 'closed') not in ('closed', 'running'):
            try:
                self.close()
            except BaseException:
                pass  # Abandonment cannot produce acceptance evidence.

    def close(self):
        pc.require(threading.get_ident() == self._owner_thread, 'single experiment owner thread')
        pc.require(self.state not in ('running', 'preparing'), 'cannot retire borrowed experiment capability')
        errors = []
        for label, owner in (('fixture', self.fixture), ('workspace', self.workspace)):
            try:
                owner.close()
                self.close_outcomes[label] = 'closed'
            except BaseException as error:
                errors.append(type(error).__name__)
                self.close_outcomes[label] = 'unproved:' + type(error).__name__
        if self._build_admission is not None:
            try:
                self._build_admission.retire()
                self.close_outcomes['admission'] = 'retired'
            except BaseException as error:
                errors.append(type(error).__name__)
                self.close_outcomes['admission'] = 'unproved:' + type(error).__name__
        self.state = 'closed'
        pc.require(not errors, 'experiment capability retirement unproved')
        # Owned files remain for review; this API never recursively deletes them.


def _records(raw, marker):
    pc.require(type(raw) is bytes and len(raw) <= bp.MAX_OUTPUT, 'owned output budget')
    values = []
    for line in raw.splitlines():
        if marker not in line:
            continue
        payload = line.split(marker, 1)[1]
        pc.require(len(values) < 16 and len(payload) <= 4096, 'native record budget')
        values.append(pc.decode_claim(payload, 4096))
    return values


def observed_process_ids(raw, fixture_claim, source_commit):
    fixture = pc.decode_claim(fixture_claim, pc.FIXTURE_BYTES)
    pids = set()
    for record in _records(raw, b'OWNED_SELECTION_PROCESS '):
        pc.keys(record, {'method', 'sourceCommit', 'runID', 'caseID', 'runnerPID', 'hostPID'})
        pc.require(record['method'] in xb.METHODS and record['sourceCommit'] == source_commit and
                   record['runID'] == fixture['runID'] and record['caseID'] == fixture['caseID'], 'foreign process record')
        for field in ('runnerPID', 'hostPID'):
            pc.require(type(record[field]) is int and 1 < record[field] < 2**31, 'process identity type')
            pids.add(record[field])
    pc.require(len(pids) <= 8, 'native process budget')
    return tuple(sorted(pids))


def verify_execution_output(result, inspection, fixture_claim):
    pc.require(type(result) is bp.ProcessResult and result.returncode == 0 and result.direct_child_reaped and result.owned_group_retired and
               not result.reason and not result.cancelled, 'successful observed child result required')
    context = pc.decode_claim(inspection.context, 65536)
    pc.require(result.arguments == (context['executable'], *context['arguments']), 'actual runtime invocation mismatch')
    raw = result.stdout + b'\n' + result.stderr
    fixture = pc.decode_claim(fixture_claim, pc.FIXTURE_BYTES); host = inspection.observations.signatures[0]
    cases = _records(raw, b'OWNED_SELECTION_CASE ')
    pc.require(len(cases) == 3 and all(type(x) is dict and type(x.get('method')) is str for x in cases) and
               {x['method'] for x in cases} == set(xb.METHODS), 'exact three observed methods')
    expected_captures = ('100-selected-read-retired', '101-panel-cancelled', '102-active-cancelled', '103-retry-retired')
    captured = []
    pids = observed_process_ids(raw, fixture_claim, inspection.source_commit)
    processes = _records(raw, b'OWNED_SELECTION_PROCESS ')
    pc.require(len(processes) == 3 and {x['method'] for x in processes} == set(xb.METHODS), 'exact three launched-process observations')
    pc.require(bool(pids), 'owned process observations required')
    by_method = {x['method']: x['hostPID'] for x in processes}
    pc.require(all(x['runnerPID'] != x['hostPID'] for x in processes), 'distinct runner/host processes')
    receipts = _records(raw, b'OWNED_SELECTION_UI_RECEIPT ')
    pc.require(len(receipts) == 4, 'four terminal observations required')
    expected = {xb.METHODS[0]: [('passed', expected_captures[0])], xb.METHODS[1]: [('panel-cancelled', expected_captures[1])],
                xb.METHODS[2]: [('read-cancelled', expected_captures[2]), ('passed', expected_captures[3])]}
    for case in cases:
        pc.keys(case, {'method', 'sourceCommit', 'runID', 'caseID'})
        pc.require(case['sourceCommit'] == inspection.source_commit and case['runID'] == fixture['runID'] and
                   case['caseID'] == fixture['caseID'], 'foreign method observation')
    for wrapper in receipts:
        pc.keys(wrapper, {'method', 'capture', 'captureSHA256', 'captureBytes', 'pixelWidth', 'pixelHeight', 'receipt'})
        method, capture, receipt = wrapper['method'], wrapper['capture'], wrapper['receipt']
        pc.require(type(method) is str and method in expected and type(receipt) is dict, 'terminal method shape')
        pc.keys(receipt, {'schemaVersion', 'sourceCommit', 'runID', 'caseID', 'pid', 'observedIdentifier', 'observedExecutable',
                          'observedCDHash', 'runningValidityChecked', 'error', 'outcome', 'borrowedWorkerRetired',
                          'scopeRetired', 'panelRetired', 'beforeOperation', 'beforeErrno', 'afterOperation', 'afterErrno',
                          'activeControls', 'positiveReadReachedControls'})
        pc.require(type(receipt['schemaVersion']) is int and receipt['schemaVersion'] == 1, 'native receipt schema')
        pair = (receipt.get('outcome'), capture)
        pc.require(pair in expected[method], 'terminal outcome/capture mismatch'); expected[method].remove(pair)
        pc.require(receipt.get('sourceCommit') == inspection.source_commit and receipt.get('runID') == fixture['runID'] and
                   receipt.get('caseID') == fixture['caseID'] and type(receipt.get('pid')) is int and receipt['pid'] == by_method[method] and
                   receipt.get('observedIdentifier') == host.identifier and receipt.get('observedExecutable') == host.executable and
                   receipt.get('observedCDHash') == host.cdhash and receipt.get('runningValidityChecked') is True and
                   receipt.get('error') == '', 'launched host differs from reviewed inspection')
        for key in ('borrowedWorkerRetired', 'scopeRetired', 'panelRetired'):
            pc.require(receipt.get(key) is True, 'native retirement observation missing')
        allowed = {'root-open', 'ancestor-open', 'selected-content-open', 'selected-content-read'}
        for stage in ('before', 'after'):
            pc.require(receipt.get(stage + 'Operation') in allowed and type(receipt.get(stage + 'Errno')) is int and
                       receipt[stage + 'Errno'] in (1, 13), 'measured selected denial required')
        controls = receipt.get('activeControls')
        size = 0 if pair[0] == 'panel-cancelled' else 4
        pc.require(type(controls) is list and len(controls) == size and receipt.get('positiveReadReachedControls') is (size == 4),
                   'positive read/control observations required')
        groups = ({'sibling-read-open'}, {'parent-stream-open', 'parent-entry-read'}, {'selected-write-open'}, {'selected-create-exclusive'})
        for control, operations in zip(controls, groups):
            pc.keys(control, {'operation', 'errno'})
            pc.require(control['operation'] in operations | {'root-open', 'ancestor-open'} and
                       type(control['errno']) is int and control['errno'] in (1, 13), 'measured active denial required')
        captured.append(capture)
    pc.require(all(not items for items in expected.values()), 'missing method terminal observation')
    return tuple(sorted(x['method'] for x in cases)), tuple(sorted(captured)), pids


def verify_capture_inventory(inventory, raw):
    rows = {json.loads(row)['path']: json.loads(row) for row in inventory}
    records = _records(raw, b'OWNED_SELECTION_UI_RECEIPT ')
    names = set()
    for record in records:
        name = record['capture'] + '.png'
        pc.require(name not in names, 'duplicate original capture'); names.add(name)
        pc.require(type(record.get('captureBytes')) is int and 0 < record['captureBytes'] <= 4 * 1024 * 1024 and
                   type(record.get('captureSHA256')) is str and re.fullmatch(r'[0-9a-f]{64}', record['captureSHA256']) and
                   all(type(record.get(k)) is int and 0 < record[k] <= 8192 for k in ('pixelWidth', 'pixelHeight')),
                   'capture observation shape')
        pc.require(name in rows and rows[name]['kind'] == 'file' and rows[name]['size'] == record['captureBytes'] and
                   rows[name]['sha256'] == record['captureSHA256'], 'original capture bytes differ')
    pc.require(len(names) == 4 and set(rows) == names | {'.'} and rows['.']['kind'] == 'directory',
               'exact four original capture files required')


if __name__ == '__main__':
    raise SystemExit(2)
