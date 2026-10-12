"""One terminal build-only attempt; source remains disabled and unexecuted.

All filesystem/process authority stays with fresh owned capabilities. Evidence
failures never skip source retirement, and a B packet cannot resume Stage C.
"""
import hashlib
import json
import math
import time

import experiment_controller as ec
import probe_contract as pc
import stage_b_admission as ba
import stage_b_profile as profile
import stage_b_receipt as sr

MAX_JSON = 16 * 1024 * 1024


def encode(value, limit=MAX_JSON):
    data = bytearray()
    for piece in json.JSONEncoder(sort_keys=True, separators=(',', ':'), allow_nan=False).iterencode(value):
        data.extend(piece.encode())
        pc.require(len(data) <= limit, 'receipt JSON byte budget')
    return bytes(data)


def error_record(label, error):
    # Nested retirement wrappers retain the initiating operation. Bound both
    # wrapper traversal and independent cleanup diagnostics; never retry here.
    cleanup = []; omitted = 0; seen = set(); current = error
    for _ in range(8):
        if id(current) in seen:
            break
        seen.add(id(current))
        values = getattr(current, 'cleanup_failures', ())
        for item in values[:256]:
            if len(cleanup) < 256:
                if type(item) is dict:
                    row = {'kind': str(item.get('kind', ''))[:80], 'message': str(item.get('message', ''))[:512],
                           'errno': item.get('errno') if type(item.get('errno')) is int else None}
                    if type(item.get('descriptor')) is int:
                        row['descriptor'] = item['descriptor']
                    if type(item.get('owner')) is str:
                        row['owner'] = item['owner'][:80]
                    cleanup.append(row)
                else:
                    cleanup.append({'kind': type(item).__name__, 'message': str(item)[:512],
                        'errno': item.errno if isinstance(item, OSError) and type(item.errno) is int else None})
            else:
                omitted += 1
        omitted += max(0, len(values) - 256) + getattr(current, 'omitted_cleanup_failure_count', 0)
        original = getattr(current, 'original', None)
        if not isinstance(original, BaseException):
            break
        current = original
    details = getattr(current, 'failures', ())
    return {'phase': label, 'kind': type(current).__name__,
            'reason': str(getattr(current, 'reason', ''))[:256], 'message': str(current)[:512],
            'errno': current.errno if isinstance(current, OSError) and type(current.errno) is int else None,
            'details': [str(item)[:1024] for item in details[:256]],
            'omitted_detail_count': max(0, len(details) - 256),
            'cleanup_failures': cleanup, 'omitted_cleanup_failure_count': omitted}


def terminal_failures(failures):
    # A missing packet must still explain the first error. Per-field UTF-8
    # limits bound the whole terminal even for non-ASCII error messages.
    def text(value, limit):
        return str(value).encode('utf-8', errors='replace')[:limit].decode('utf-8', errors='ignore')
    result = []
    for index, item in enumerate(failures[:16]):
        result.append({key: text(item.get(key, ''), limit) for key, limit in
                       (('phase', 128), ('kind', 80), ('reason', 160),
                        ('message', 512 if index == 0 else 256))})
        number = item.get('errno')
        result[-1]['errno'] = number if type(number) is int and -(2**31) <= number < 2**31 else None
        try:
            encode(result, 14000)
        except pc.Refusal:
            result.pop()
            break
    return result


def run(identity, host_files, *, started_at):
    pc.require(profile.BUILD_ONLY_ENABLED is True, 'build-only profile disabled')
    pc.require(type(started_at) in (int, float) and math.isfinite(started_at), 'driver clock')
    pc.require(type(identity) is dict and type(host_files) is dict, 'verified startup data')
    pc.require(identity.get('GITHUB_REPOSITORY') == profile.REPOSITORY and
               identity.get('GITHUB_REF') == profile.REF and identity.get('GITHUB_EVENT_NAME') == 'create' and
               identity.get('CREATED_REF_TYPE') == 'branch' and
               identity.get('CREATED_REF') == profile.REF.removeprefix('refs/heads/') and
               identity.get('GITHUB_RUN_ATTEMPT') == '1', 'driver dispatch identity')
    # Bootstrap supplied immutable source bytes, verified before project imports.
    pc.require(ec._source_files(host_files) == profile.HOST_ROWS, 'driver host source rows')
    deadline = started_at + 900
    report = experiment = inspection = admission = None
    failures = []; collected = {}; terminal = None
    last_finalisation_clock = started_at

    def finalisation_check():
        nonlocal last_finalisation_clock
        now = time.monotonic()
        pc.require(math.isfinite(now) and last_finalisation_clock <= now < deadline, 'finalisation deadline')
        last_finalisation_clock = now

    def attempt(label, operation):
        try:
            finalisation_check()
            return operation()
        except BaseException as error:
            failures.append(error_record(label, error))
            return None

    def export(name, data):
        if report is not None:
            return attempt('export:' + name, lambda: report.add(name, data))
        return None

    try:
        pc.require(started_at <= time.monotonic() < started_at + 720, 'driver work deadline')
        admission = ba._issue(started_at)
        report = sr.Report.create(deadline=deadline)
        experiment = ec.Experiment.prepare(profile.HOST_SOURCE_COMMIT, host_files, admission=admission)
        inspection = experiment.inspect_b()
    except BaseException as error:
        failures.append(error_record('prepare-or-build', error))
        if isinstance(error, ec.PreparationFailure):
            collected['preparation_retirement'] = error.dispositions
        if admission is not None:
            try:
                admission.stop()
            except BaseException as secondary:
                failures.append(error_record('admission-stop', secondary))
    finally:
        try:
            # These observations are independent: an export or disposition failure
            # never skips another owner, close, or safe evidence attempt.
            export('identity.json', attempt('identity-json', lambda: encode(identity, 65536)) or b'{}')
            export('source-manifest.json', encode({'hostSourceCommit': profile.HOST_SOURCE_COMMIT,
                                                  'rows': profile.HOST_ROWS}, 32768))
            if experiment is not None:
                export('fixture.json', experiment.fixture.claim)
                raw = attempt('configuration-capture', lambda: sr.capture_configurations(experiment.workspace, deadline=deadline))
                if raw is not None:
                    collected['configuration_capture'] = {'failures': raw.failures,
                        'leaves': [{'name': item.name, 'refusals': item.refusals} for item in raw.captures]}
                    for index, item in enumerate(raw.captures):
                        if item.data is not None:
                            export('configuration-' + str(index) + '.bin', item.data)
                        failures.extend({'phase': 'configuration:' + item.name, 'kind': str(reason), 'reason': ''}
                                        for reason in item.refusals)
                    failures.extend({'phase': 'configuration-capture', 'kind': str(reason), 'reason': ''}
                                    for reason in raw.failures)
                for label, operation in (
                        ('fixture', lambda: experiment.fixture.verify(check=finalisation_check)),
                        ('source', lambda: ec._verify_inputs(experiment.workspace, experiment.input_rows, check=finalisation_check)),
                        ('products', lambda: experiment.workspace.inventory(check=finalisation_check)),
                        ('captures', lambda: experiment.workspace.inventory(captures=True, check=finalisation_check))):
                    collected[label] = attempt('disposition:' + label, operation)
                # First failure observations are historical and independent of
                # the later checks above. Never overwrite them with a later pass.
                first = dict(experiment.failure_evidence)
                results = list(experiment.trace)
                first_results = first.pop('tool_results', ())
                extra = first.pop('untraced_failure_result', None)
                pc.require(type(first_results) is tuple and len(first_results) <= 64,
                           'first failure tool count')
                if extra is not None:
                    first_results += (extra,)
                references = []
                for item in first_results:
                    pc.require(type(item) is ec.bp.ProcessResult, 'first failure process result')
                    found = next((i for i, recorded in enumerate(results) if recorded is item), None)
                    if found is None:
                        pc.require(len(results) < 65, 'combined tool count')
                        results.append(item); found = len(results) - 1
                    references.append(found)
                pc.require(sum(len(item.stdout) + len(item.stderr) for item in results) <= ec.TOTAL_LOG_BYTES,
                           'combined raw tool byte budget')
                first['tool_result_indices'] = references
                export('first-failure.json', attempt('first-failure-json', lambda: encode(first)) or b'{}')
                metadata = []
                for index, item in enumerate(results):
                    export('tool-%02d-stdout.bin' % index, item.stdout)
                    export('tool-%02d-stderr.bin' % index, item.stderr)
                    metadata.append({'arguments': item.arguments, 'returncode': item.returncode, 'reason': item.reason,
                                     'direct_child_reaped': item.direct_child_reaped, 'owned_group_retired': item.owned_group_retired,
                                     'cancelled': item.cancelled, 'stdout_sha256': hashlib.sha256(item.stdout).hexdigest(),
                                     'stderr_sha256': hashlib.sha256(item.stderr).hexdigest()})
                export('tool-results.json', attempt('tool-json', lambda: encode(metadata, 131072)) or b'[]')
                export('generated-rows.json', encode(experiment.generated_rows, 32768))
                generated = attempt('generated-bytes', lambda: ec._verify_inputs(experiment.workspace, experiment.generated_rows, retain=True, check=finalisation_check))
                if generated is not None:
                    for index, (_, data) in enumerate(sorted(generated.items())):
                        export('generated-%d.bin' % index, data)
                if inspection is not None:
                    raw_inspection = attempt('inspection-json', lambda: encode(ec._canonical(inspection)))
                    if raw_inspection is not None:
                        export('inspection.json', raw_inspection)
                        collected['inspection_digest'] = ec.inspection_digest(inspection)
        except BaseException as error:
            failures.append(error_record('evidence-assembly', error))
        finally:
            if experiment is not None:
                try:
                    experiment.close()
                except BaseException as error:
                    failures.append(error_record('source-retirement', error))
                collected['source_retirement'] = experiment.close_outcomes
            elif admission is not None:
                try:
                    admission.retire()
                except BaseException as error:
                    failures.append(error_record('admission-retirement', error))
        if report is not None:
            try:
                # Everything needed from source owners was collected before close.
                export('dispositions.json', attempt('disposition-json', lambda: encode(collected)) or b'{}')
                outcome = {'outcome': 'candidate_pass' if inspection is not None and not failures else 'failed',
                           'failures': failures, 'newHostLaunched': False, 'stageCEnabled': False,
                           'runID': identity.get('GITHUB_RUN_ID'), 'driverCommit': identity.get('GITHUB_SHA')}
                terminal = report.finalise(encode(outcome, 1024 * 1024))
            except BaseException as error:
                failures.append(error_record('report-finalisation', error))
                # ReportFailure's path is present only for a safely finalised,
                # closed failure packet. Never invent a path after partial export.
                if type(error) is sr.ReportFailure and error.receipt is not None:
                    terminal = error.receipt
                try:
                    collected['report_abort'] = report.abort()
                except BaseException as secondary:
                    failures.append(error_record('report-abort', secondary))
    passed = terminal is not None and terminal.outcome == 'candidate_pass' and not failures
    projected = terminal_failures(failures)
    message = {'outcome': 'candidate_pass' if passed else 'failed',
               'runID': identity.get('GITHUB_RUN_ID'), 'driverCommit': identity.get('GITHUB_SHA'),
               'report_path': terminal.path if terminal is not None else collected.get('failed_report_path'),
               'manifest_sha256': terminal.manifest_sha256 if terminal is not None else None,
               'manifest_bytes': terminal.manifest_bytes if terminal is not None else None,
               'root_device': terminal.root_device if terminal is not None else None,
               'root_inode': terminal.root_inode if terminal is not None else None,
               'failure_count': len(failures),
               'omitted_failure_count': len(failures) - len(projected),
               'failures': projected}
    print('OWNED_BUILD_TERMINAL ' + encode(message, 16384).decode())
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(2)  # No direct CLI, paths, environment gate or alternate mode.
