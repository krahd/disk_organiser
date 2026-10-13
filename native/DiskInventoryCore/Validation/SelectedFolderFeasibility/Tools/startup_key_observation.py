"""One startup-key observation only. No operational module or main is included.

The standard-library imports and named admission/observation helpers below are
byte-exact copies of the reviewed bootstrap, enforced by memory-only tests.
No matching or mismatching key result permits a build or further operation.
"""
import ast


import hashlib


import json


import os


import re


import stat


import sys


import types


import time


import plistlib


import math


CHECKOUT = '/Users/runner/work/disk_organiser/disk_organiser'


RELATIVE = 'native/DiskInventoryCore/Validation/SelectedFolderFeasibility'


MODULES = ('probe_contract', 'xctestrun_binding', 'runner_expectations',
           'owned_build_observation', 'fixture_inputs', 'bounded_process',
           'native_observations', 'stage_b_commands', 'stage_b_admission',
           'experiment_controller', 'stage_b_receipt', 'stage_b_upload', 'stage_b_driver')


PROFILE_FIELDS = {'BUILD_ONLY_ENABLED', 'HOST_SOURCE_COMMIT', 'HOST_ROWS_SHA256', 'HOST_ROWS',
                  'WORKFLOW', 'TEMPLATE', 'REPOSITORY', 'REF', 'PYTHON', 'MODULE_ROWS'}


STARTUP_FIXED = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C', 'LC_ALL': 'C'}


STARTUP_IDENTITY = frozenset({
    'EXPECTED_DRIVER_SHA', 'GITHUB_EVENT_NAME', 'GITHUB_REPOSITORY', 'GITHUB_REF',
    'CREATED_REF', 'CREATED_REF_TYPE',
    'GITHUB_SHA', 'CHECKED_OUT_SHA', 'GITHUB_WORKFLOW_SHA', 'GITHUB_RUN_ATTEMPT',
    'GITHUB_WORKFLOW_REF', 'GITHUB_WORKSPACE', 'GITHUB_RUN_ID', 'ImageOS', 'ImageVersion'})


STARTUP_KEYS = STARTUP_IDENTITY | STARTUP_FIXED.keys()


STARTUP_KNOWN_SYSTEM_KEYS = ('LC_CTYPE', '__PYVENV_LAUNCHER__', '__CF_USER_TEXT_ENCODING', '_')


STARTUP_DIAGNOSTIC_COUNT_CAP = 256


class Refusal(Exception):
    pass


def require(value, message):
    if not value:
        raise Refusal(message)


def startup_key_diagnostic(observed_keys):
    """Finite data-only mismatch summary; never inspect or retain any values.

    Missing names come only from the fixed expected set. Unknown names are not
    emitted, hashed or retained. Membership work is over fixed sets; counts
    saturate explicitly. This does not admit any additional environment key.
    """
    require(type(observed_keys) is set, 'startup key observation type')
    missing = sorted(STARTUP_KEYS - observed_keys)
    known = {name: name in observed_keys for name in STARTUP_KNOWN_SYSTEM_KEYS}
    unexpected = len(observed_keys) - (len(STARTUP_KEYS) - len(missing))
    unknown = unexpected - sum(known.values())
    cap = STARTUP_DIAGNOSTIC_COUNT_CAP
    return {'schema': 1, 'missing_expected': missing,
            'unexpected_count': min(unexpected, cap),
            'unexpected_count_capped': unexpected > cap,
            'known_system_presence': known,
            'unknown_count': min(unknown, cap),
            'unknown_count_capped': unknown > cap}


def interpreter_identity(profile):
    """Bounded observed facts, not authentication of loaded interpreter bytes.

    The versioned framework launcher removes the documented cache alias. Its
    reported path is still an exact admission check, never resolved or relaxed.
    No filesystem/process operation or operational project import occurs here.
    """
    executable = sys.executable
    implementation = sys.implementation.name
    platform = sys.platform
    machine = os.uname().machine
    require(isinstance(sys.version_info, tuple) and 3 <= len(sys.version_info) <= 5,
            'interpreter version shape')
    version = tuple(sys.version_info[:3])
    flags = {name: getattr(sys.flags, name) for name in
             ('isolated', 'no_site', 'dont_write_bytecode')}
    strings = ((executable, 256), (implementation, 16), (platform, 16), (machine, 16))
    require(all(type(value) is str and 0 < len(value) <= limit and value.isascii() and
                '\0' not in value for value, limit in strings), 'interpreter fact string bounds')
    require(profile['PYTHON'] == '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12' and
            executable == profile['PYTHON'], 'fixed framework interpreter')
    require(len(version) == 3 and all(type(value) is int and 0 <= value <= 65535 for value in version)
            and version == (3, 12, 10), 'fixed interpreter version')
    require(implementation == 'cpython', 'fixed interpreter implementation')
    require(all(type(value) is int and value == 1 for value in flags.values()),
            'isolated no-bytecode interpreter facts')
    require(platform == 'darwin' and machine == 'arm64', 'fixed native runner')
    # Exact seven-key schema: bounded ASCII strings, three integers and three
    # fixed integer flags. The existing identity.json envelope remains 64 KiB.
    return {'schema': 1, 'executable': executable, 'version': list(version),
            'implementation': implementation, 'flags': flags,
            'platform': platform, 'machine': machine}


def _stamp(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
            value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def read_source(relative, limit, *, _system=False, check=None):
    """Finite no-follow source reads only; no output or experiment creation."""
    require(type(relative) is str and re.fullmatch(r'[A-Za-z0-9_./-]+', relative) and
            all(x not in ('', '.', '..') for x in relative.split('/')), 'source relative name')
    require(not _system or (relative == 'System/Library/CoreServices/SystemVersion.plist' and limit == 4096),
            'fixed system version source')
    descriptors = []; first = None; result = None
    budget = check if check is not None else lambda: None
    try:
        budget()
        parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        descriptors.append(parent)
        parts = relative.split('/') if _system else CHECKOUT.strip('/').split('/') + relative.split('/')
        for part in parts[:-1]:
            budget()
            parent = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            descriptors.append(parent)
        budget()
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        descriptors.append(descriptor)
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                before.st_uid == (0 if _system else os.getuid()) and 0 < before.st_size <= limit, 'source type/size/owner')
        data = bytearray()
        for _ in range(4096):
            budget()
            try:
                part = os.read(descriptor, min(65536, before.st_size + 1 - len(data)))
            except InterruptedError:
                continue
            if not part:
                break
            data.extend(part)
            require(len(data) <= before.st_size, 'source grew')
        budget()
        named = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        require(len(data) == before.st_size and _stamp(before) == _stamp(os.fstat(descriptor)) == _stamp(named),
                'source read identity/stamp')
        result = bytes(data)
    except BaseException as error:
        first = error
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except BaseException as error:
                first = first or Refusal('ambiguous source close:' + type(error).__name__)
    if first is not None:
        raise first
    return result


def decode_profile(raw, expected_normalised_sha256):
    require(type(raw) is bytes and 0 < len(raw) <= 32768 and
            re.fullmatch(r'[0-9a-f]{64}', expected_normalised_sha256), 'profile bounds/hash')
    tree = ast.parse(raw); values = {}; boolean = None
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and type(node.value.value) is str:
            continue
        require(isinstance(node, ast.Assign) and len(node.targets) == 1 and
                isinstance(node.targets[0], ast.Name), 'literal profile only')
        name = node.targets[0].id
        require(name in PROFILE_FIELDS and name not in values, 'profile fields')
        values[name] = ast.literal_eval(node.value)
        if name == 'BUILD_ONLY_ENABLED':
            require(type(values[name]) is bool and node.lineno == node.end_lineno, 'literal build flag')
            boolean = node
    require(set(values) == PROFILE_FIELDS and boolean is not None, 'complete profile')
    lines = raw.decode('utf-8', errors='strict').splitlines(keepends=True)
    require(lines[boolean.lineno - 1] in ('BUILD_ONLY_ENABLED = False\n', 'BUILD_ONLY_ENABLED = True\n'),
            'exact activation flag line')
    lines[boolean.lineno - 1] = 'BUILD_ONLY_ENABLED = False\n'
    normalised = ''.join(lines).encode()
    require(hashlib.sha256(normalised).hexdigest() == expected_normalised_sha256, 'profile hash mismatch')
    require(type(values['HOST_ROWS']) is tuple and len(values['HOST_ROWS']) == 19 and
            type(values['MODULE_ROWS']) is tuple and len(values['MODULE_ROWS']) == len(MODULES) + 1,
            'fixed source row counts')
    return values


def system_version(*, check=None):
    options = {'_system': True}
    if check is not None:
        options['check'] = check
    raw = read_source('System/Library/CoreServices/SystemVersion.plist', 4096, **options)
    value = plistlib.loads(raw)
    require(type(value) is dict and type(value.get('ProductVersion')) is str and
            type(value.get('ProductBuildVersion')) is str, 'system version fields')
    match = re.fullmatch(r'15\.([0-9]{1,2})(?:\.([0-9]{1,2}))?', value['ProductVersion'])
    require(match is not None and int(match.group(1)) >= 3, 'macOS15 minimum15.3')
    return {'version': value['ProductVersion'], 'build': value['ProductBuildVersion'],
            'machine': os.uname().machine, 'source_sha256': hashlib.sha256(raw).hexdigest()}



ENTRY = RELATIVE + '/Tools/startup_key_observation.py'
WORKFLOW = '.github/workflows/owned-startup-key-observation.yml'
TEMPLATE = RELATIVE + '/StageB/owned-startup-key-observation.yml.inert'
REF = 'refs/heads/validation/startup-keys-once-20261013'
PROFILE_HASH = '9185bcf82855edff5a5e8eef9c63f67a6cd307aa9b8a7db4d35fde4a88dfab42'
ARGUMENT_NAMES = ('ENTRY_SHA256', 'EXPECTED_DRIVER_SHA', 'CREATED_REF', 'CREATED_REF_TYPE',
                 'GITHUB_EVENT_NAME', 'GITHUB_REPOSITORY', 'GITHUB_REF', 'GITHUB_SHA',
                 'CHECKED_OUT_SHA', 'GITHUB_WORKFLOW_SHA', 'GITHUB_RUN_ATTEMPT',
                 'GITHUB_WORKFLOW_REF', 'GITHUB_WORKSPACE', 'GITHUB_RUN_ID',
                 'ImageOS', 'ImageVersion')
REASONS = frozenset({'arguments', 'clock', 'source', 'profile', 'runtime', 'system', 'observation', 'output'})
PREFIX = 'OWNED_STARTUP_KEYS '


def dispatch_arguments(arguments):
    require(type(arguments) is list and len(arguments) == len(ARGUMENT_NAMES), 'arguments')
    require(all(type(v) is str and 0 < len(v) <= 4096 and v.isascii() and
                not any(ch in v for ch in ('\0', '\r', '\n')) for v in arguments), 'arguments')
    value = dict(zip(ARGUMENT_NAMES, arguments))
    sha = value['EXPECTED_DRIVER_SHA']
    require(re.fullmatch(r'[0-9a-f]{64}', value['ENTRY_SHA256']) and
            re.fullmatch(r'[0-9a-f]{40}', sha), 'arguments')
    fixed = {'CREATED_REF': REF.removeprefix('refs/heads/'), 'CREATED_REF_TYPE': 'branch',
             'GITHUB_EVENT_NAME': 'create', 'GITHUB_REPOSITORY': 'krahd/disk_organiser',
             'GITHUB_REF': REF, 'GITHUB_SHA': sha, 'CHECKED_OUT_SHA': sha,
             'GITHUB_WORKFLOW_SHA': sha, 'GITHUB_RUN_ATTEMPT': '1',
             'GITHUB_WORKFLOW_REF': 'krahd/disk_organiser/' + WORKFLOW + '@' + REF,
             'GITHUB_WORKSPACE': CHECKOUT, 'ImageOS': 'macos15'}
    require(all(value[k] == v for k, v in fixed.items()), 'arguments')
    require(re.fullmatch(r'[1-9][0-9]{0,19}', value['GITHUB_RUN_ID']) and
            re.fullmatch(r'[0-9.]{1,64}', value['ImageVersion']), 'arguments')
    return value


def inconclusive(reason):
    # Never interpolate exception text, environment names/values or argv.
    return {'schema': 1, 'outcome': 'inconclusive',
            'reason': reason if reason in REASONS else 'output'}


def observe(arguments):
    phase = 'arguments'
    try:
        context = dispatch_arguments(arguments)
        phase = 'clock'
        start = time.monotonic()
        require(math.isfinite(start), 'clock')
        previous = start
        def check():
            nonlocal previous
            now = time.monotonic()
            require(math.isfinite(now) and previous <= now < start + 45, 'clock')
            previous = now
        phase = 'source'
        check()
        raw = read_source(ENTRY, 32768, check=check)
        require(hashlib.sha256(raw).hexdigest() == context['ENTRY_SHA256'], 'source')
        workflow = read_source(WORKFLOW, 16384, check=check)
        require(workflow == read_source(TEMPLATE, 16384, check=check), 'source')
        phase = 'profile'
        profile = decode_profile(read_source(RELATIVE + '/Tools/stage_b_profile.py', 32768,
                                             check=check), PROFILE_HASH)
        require(profile['BUILD_ONLY_ENABLED'] is False, 'profile')
        phase = 'runtime'
        interpreter_identity(profile)
        phase = 'system'
        system_version(check=check)
        phase = 'observation'
        check()
        # The one observation is the real post-startup mapping, unfiltered and
        # unreconstructed. Do not call startup_environment or read its values.
        observed_keys = set(os.environ)
        diagnostic = startup_key_diagnostic(observed_keys)
        matched = observed_keys == STARTUP_KEYS
        del observed_keys
        check()
        return {'schema': 1, 'outcome': 'keys_match' if matched else 'keys_mismatch',
                'environment_keys': diagnostic}
    except BaseException:
        return inconclusive(phase)


def encode_record(record):
    # Only locally constructed primitive records reach this function. The
    # fallback is fixed and itself bounded; no repr/traceback is a data channel.
    try:
        require(type(record) is dict and type(record.get('schema')) is int and record['schema'] == 1, 'output')
        if record.get('outcome') == 'inconclusive':
            require(set(record) == {'schema', 'outcome', 'reason'} and record['reason'] in REASONS, 'output')
        else:
            require(set(record) == {'schema', 'outcome', 'environment_keys'} and
                    record['outcome'] in ('keys_match', 'keys_mismatch'), 'output')
            diagnostic = record['environment_keys']
            require(type(diagnostic) is dict and set(diagnostic) ==
                    {'schema', 'missing_expected', 'unexpected_count', 'unexpected_count_capped',
                     'known_system_presence', 'unknown_count', 'unknown_count_capped'}, 'output')
            require(type(diagnostic['schema']) is int and diagnostic['schema'] == 1, 'output')
            missing = diagnostic['missing_expected']
            require(type(missing) is list and len(missing) <= len(STARTUP_KEYS) and
                    all(type(k) is str and k in STARTUP_KEYS for k in missing) and
                    missing == sorted(set(missing)), 'output')
            known = diagnostic['known_system_presence']
            require(type(known) is dict and set(known) == set(STARTUP_KNOWN_SYSTEM_KEYS) and
                    all(type(v) is bool for v in known.values()), 'output')
            for key in ('unexpected_count', 'unknown_count'):
                require(type(diagnostic[key]) is int and 0 <= diagnostic[key] <= STARTUP_DIAGNOSTIC_COUNT_CAP, 'output')
                require(type(diagnostic[key + '_capped']) is bool and
                        (not diagnostic[key + '_capped'] or diagnostic[key] == STARTUP_DIAGNOSTIC_COUNT_CAP), 'output')
            total_floor = diagnostic['unknown_count'] + sum(known.values())
            require(diagnostic['unexpected_count'] == min(total_floor, STARTUP_DIAGNOSTIC_COUNT_CAP) and
                    diagnostic['unexpected_count_capped'] ==
                    (diagnostic['unknown_count_capped'] or total_floor > STARTUP_DIAGNOSTIC_COUNT_CAP), 'output')
            matches = not missing and diagnostic['unexpected_count'] == 0
            require((record['outcome'] == 'keys_match') == matches, 'output')
        line = PREFIX + json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False)
        require(len((line + '\n').encode('utf-8')) <= 2048, 'output')
        return line
    except BaseException:
        return PREFIX + '{"outcome":"inconclusive","reason":"output","schema":1}'


def cli(arguments):
    record = observe(arguments)
    line = encode_record(record)
    print(line)
    return 0 if record['outcome'] == 'keys_match' and '"reason":"output"' not in line else 2


if __name__ == '__main__':
    raise SystemExit(cli(sys.argv[1:]))
