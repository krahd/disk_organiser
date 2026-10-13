"""Fixed checkout bootstrap. No operational import precedes source admission.

The template pins this script through the complete profile's module rows. The
reviewed GitHub workflow/checkout is the initial trust anchor, not Python privacy.
Only the profile's single reviewed Boolean is normalised for its activation hash.
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
                  'WORKFLOW', 'TEMPLATE', 'REPOSITORY', 'REF', 'PYTHON', 'MODULE_ROWS',
                  'EXPECTED_RUN_NUMBER'}
STARTUP_FIXED = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C', 'LC_ALL': 'C'}
STARTUP_IDENTITY = frozenset({
    'EXPECTED_DRIVER_SHA', 'GITHUB_EVENT_NAME', 'GITHUB_REPOSITORY', 'GITHUB_REF',
    'CREATED_REF', 'CREATED_REF_TYPE',
    'GITHUB_SHA', 'CHECKED_OUT_SHA', 'GITHUB_WORKFLOW_SHA', 'GITHUB_RUN_ATTEMPT',
    'GITHUB_WORKFLOW_REF', 'GITHUB_WORKSPACE', 'GITHUB_RUN_ID', 'ImageOS', 'ImageVersion'})
STARTUP_KEYS = STARTUP_IDENTITY | STARTUP_FIXED.keys()
# Presence-only diagnostic names; the admission rule below is separate.
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


class StartupEnvironmentRefusal(Refusal):
    def __init__(self, observed_keys):
        super().__init__('startup environment keys')
        # Only the detached fixed-schema primitive summary survives the raise.
        self.key_diagnostic = startup_key_diagnostic(observed_keys)


def startup_refusal_record(error):
    record = {'kind': type(error).__name__, 'message': str(error)[:512],
              'platform': sys.platform, 'python': list(sys.version_info[:3]),
              'executable': sys.executable[:512]}
    if type(error) is StartupEnvironmentRefusal:
        record['environment_keys'] = error.key_diagnostic
    return record


def startup_environment(environment):
    """Validate the env -i contract; copy only its explicit non-secret keys.

    Called after exact Darwin/interpreter admission in main. The sole optional
    encoding marker is observed by name only, never read, copied or removed.
    Its ambient value can still influence platform code; this is not a safety
    or authenticity claim. All other key deviations refuse before value access.
    Required values retain their existing bounds and later identity checks.
    """
    observed_keys = set(environment)
    if observed_keys != STARTUP_KEYS and observed_keys != STARTUP_KEYS | {'__CF_USER_TEXT_ENCODING'}:
        raise StartupEnvironmentRefusal(observed_keys)
    result = {name: environment[name] for name in STARTUP_KEYS}
    require(all(type(value) is str and 0 < len(value) <= 4096 and '\0' not in value
                for value in result.values()), 'startup environment values')
    require(all(result[name] == value for name, value in STARTUP_FIXED.items()),
            'fixed startup environment')
    return result



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
    number = values['EXPECTED_RUN_NUMBER']
    # Zero is an unconfigured source-only sentinel, never an admissible run.
    require(type(number) is int and 0 <= number <= 1_000_000_000 and
            (number > 0 or values['BUILD_ONLY_ENABLED'] is False), 'profile run number')
    return values


def parse_run_number(actual):
    # Deliberately stricter than GitHub's loose numeric expression equality.
    require(type(actual) is str and 1 <= len(actual) <= 10 and
            re.fullmatch(r'[1-9][0-9]{0,9}', actual) is not None, 'run number spelling')
    number = int(actual)
    require(number <= 1_000_000_000, 'run number bound')
    return number


def verify_run_number(actual, profile):
    expected = profile['EXPECTED_RUN_NUMBER']
    require(type(expected) is int and 1 <= expected <= 1_000_000_000,
            'unconfigured run number')
    number = parse_run_number(actual)
    require(number == expected, 'run number mismatch')
    return number


def verify_dispatch(environment, workflow, template, profile):
    require(type(environment) is dict and workflow == template and 0 < len(workflow) <= 32768, 'exact workflow bytes')
    expected = environment.get('EXPECTED_DRIVER_SHA', '')
    require(type(expected) is str and re.fullmatch(r'[0-9a-f]{40}', expected), 'expected driver SHA')
    required = {'GITHUB_EVENT_NAME': 'create', 'GITHUB_REPOSITORY': profile['REPOSITORY'],
                'CREATED_REF_TYPE': 'branch', 'CREATED_REF': profile['REF'].removeprefix('refs/heads/'),
                'GITHUB_REF': profile['REF'], 'GITHUB_SHA': expected, 'CHECKED_OUT_SHA': expected,
                'GITHUB_WORKFLOW_SHA': expected, 'GITHUB_RUN_ATTEMPT': '1',
                'GITHUB_WORKFLOW_REF': profile['REPOSITORY'] + '/' + profile['WORKFLOW'] + '@' + profile['REF'],
                'GITHUB_WORKSPACE': CHECKOUT}
    require(all(environment.get(k) == v for k, v in required.items()), 'dispatch/checkout identity')
    require(re.fullmatch(r'[1-9][0-9]{0,19}', environment.get('GITHUB_RUN_ID', '')), 'run identity')
    return {**required, 'GITHUB_RUN_ID': environment['GITHUB_RUN_ID'], 'EXPECTED_DRIVER_SHA': expected,
            'workflow_sha256': hashlib.sha256(workflow).hexdigest()}


def admit_sources(profile, read):
    expected_names = {name + '.py' for name in MODULES} | {'stage_b_bootstrap.py'}
    require({row[0] for row in profile['MODULE_ROWS']} == expected_names and
            len(profile['MODULE_ROWS']) == len(expected_names), 'complete module closure')
    source = {}; total = 0
    for name, digest in profile['MODULE_ROWS']:
        require(type(name) is str and re.fullmatch(r'[a-z_]+\.py', name) and
                type(digest) is str and re.fullmatch(r'[0-9a-f]{64}', digest), 'module identity row')
        raw = read(RELATIVE + '/Tools/' + name, 262144)
        total += len(raw)
        require(total <= 2 * 1024 * 1024 and hashlib.sha256(raw).hexdigest() == digest, 'module bytes:' + name)
        source[name[:-3]] = raw
    host = {}
    for name, digest in profile['HOST_ROWS']:
        require(type(digest) is str and re.fullmatch(r'[0-9a-f]{64}', digest), 'host hash')
        raw = read(RELATIVE + '/' + name, 262144)
        total += len(raw)
        require(total <= 2 * 1024 * 1024 and hashlib.sha256(raw).hexdigest() == digest, 'host bytes:' + name)
        host[name] = raw
    require(hashlib.sha256(json.dumps(list(profile['HOST_ROWS']), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            == profile['HOST_ROWS_SHA256'], 'host rows digest')
    return source, host


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


def load_modules(profile, source, *, check=None):
    # Compile the already verified bytes, never reopen a path between hash/import.
    sys.modules['stage_b_bootstrap'] = sys.modules[__name__]
    names = ('stage_b_profile',) + MODULES
    require(all(name not in sys.modules for name in names), 'preloaded project module')
    module = types.ModuleType('stage_b_profile')
    module.__file__ = CHECKOUT + '/' + RELATIVE + '/Tools/stage_b_profile.py'
    module.__dict__.update(profile); sys.modules['stage_b_profile'] = module
    for name in MODULES:
        if check is not None:
            check()
        module = types.ModuleType(name)
        module.__file__ = CHECKOUT + '/' + RELATIVE + '/Tools/' + name + '.py'
        sys.modules[name] = module
        exec(compile(source[name], module.__file__, 'exec'), module.__dict__)
    return sys.modules['stage_b_driver']


def main(expected_profile_hash, actual_run_number):
    started_at = time.monotonic()
    require(math.isfinite(started_at), 'startup clock')
    last_clock = started_at
    def work_check():
        nonlocal last_clock
        now = time.monotonic()
        require(math.isfinite(now) and last_clock <= now < started_at + 720, 'startup work deadline')
        last_clock = now
    def read(relative, limit):
        return read_source(relative, limit, check=work_check)
    # The default operational gate is checked before experiment/output creation.
    require(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode, 'isolated no-bytecode startup')
    raw = read(RELATIVE + '/Tools/stage_b_profile.py', 32768)
    profile = decode_profile(raw, expected_profile_hash)
    require(profile['BUILD_ONLY_ENABLED'] is True, 'build-only profile disabled')
    interpreter = interpreter_identity(profile)
    environment = startup_environment(os.environ)
    identity = verify_dispatch(environment, read(profile['WORKFLOW'], 32768),
                               read(profile['TEMPLATE'], 32768), profile)
    # Exact dispatch/workflow/source identity precedes this immutable counter.
    # Both checks precede operational source imports and every build owner.
    identity['run_number'] = verify_run_number(actual_run_number, profile)
    source, host = admit_sources(profile, read)
    identity['interpreter'] = interpreter
    identity['profile_sha256'] = hashlib.sha256(raw).hexdigest()
    identity['profile_normalised_sha256'] = expected_profile_hash
    identity['module_rows'] = profile['MODULE_ROWS']
    identity['system'] = system_version(check=work_check)
    identity['image_os'] = environment.get('ImageOS', '')
    identity['image_version'] = environment.get('ImageVersion', '')
    require(identity['image_os'] == 'macos15' and re.fullmatch(r'[0-9.]{1,64}', identity['image_version']),
            'runner image metadata')
    work_check()
    driver = load_modules(profile, source, check=work_check)
    work_check()
    return driver.run(identity, host, started_at=started_at)


if __name__ == '__main__':
    # The hash is literal; the counter is one quoted Actions-context argument.
    if len(sys.argv) != 3 or not re.fullmatch(r'[0-9a-f]{64}', sys.argv[1]):
        raise SystemExit(2)
    try:
        result = main(sys.argv[1], sys.argv[2])
    except BaseException as error:
        print('OWNED_BUILD_STARTUP_REFUSED ' + json.dumps(
            startup_refusal_record(error), sort_keys=True, separators=(',', ':')))
        raise SystemExit(2)
    raise SystemExit(result)
