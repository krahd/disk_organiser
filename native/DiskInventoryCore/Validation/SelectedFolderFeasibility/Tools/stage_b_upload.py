"""Read-only validation of one retired report before artifact upload.

A report identity is data only. This verifier never acquires source/build
ownership, creates an experiment, launches a command or resumes Stage C.
"""
import hashlib
import json
import os
import re
import stat
import time
import math

MAX_TOTAL = 64 * 1024 * 1024
MAX_FILES = 96


def require(value, message):
    if not value:
        raise ValueError(message)


def stamp(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid,
            value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def decode(raw, limit):
    require(type(raw) is bytes and 0 < len(raw) <= limit, 'JSON bounds')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key'); result[key] = value
        return result
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('JSON constant')))


def read_leaf(parent, name, limit, deadline):
    require(type(name) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}', name), 'packet leaf')
    fd = None; first = None; raw = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and stat.S_IMODE(before.st_mode) == 0o600 and
                before.st_uid == os.getuid() and before.st_nlink == 1 and 0 <= before.st_size <= limit,
                'packet file shape')
        data = bytearray()
        for _ in range(4096):
            require(time.monotonic() < deadline, 'packet verification deadline')
            try:
                part = os.read(fd, min(65536, before.st_size + 1 - len(data)))
            except InterruptedError:
                continue
            if not part:
                break
            data.extend(part); require(len(data) <= before.st_size, 'packet grew')
        require(len(data) == before.st_size and stamp(before) == stamp(os.fstat(fd)) ==
                stamp(os.stat(name, dir_fd=parent, follow_symlinks=False)), 'packet changed')
        raw = bytes(data)
    except BaseException as error:
        first = error
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except BaseException:
                first = first or ValueError('packet file close unproved')
    if first is not None:
        raise first
    return raw


def verify_packet(raw_terminal, environment):
    require(type(raw_terminal) is str and raw_terminal.startswith('OWNED_BUILD_TERMINAL ') and
            '\n' not in raw_terminal and len(raw_terminal.encode()) <= 16384, 'one terminal record')
    record = decode(raw_terminal.removeprefix('OWNED_BUILD_TERMINAL ').encode(), 16384)
    require(type(record) is dict and record.get('outcome') in ('candidate_pass', 'failed') and
            record.get('runID') == environment.get('GITHUB_RUN_ID') and
            record.get('driverCommit') == environment.get('GITHUB_SHA'), 'terminal run identity')
    require(type(record.get('runID')) is str and re.fullmatch(r'[1-9][0-9]{0,19}', record['runID']) and
            type(record.get('driverCommit')) is str and re.fullmatch(r'[0-9a-f]{40}', record['driverCommit']), 'terminal identity shape')
    path = record.get('report_path')
    require(type(path) is str and re.fullmatch(r'/private/tmp/disk-selection-report-[A-Za-z0-9_-]{1,64}', path), 'report path')
    require(type(record.get('root_device')) is int and type(record.get('root_inode')) is int and
            record['root_device'] >= 0 and record['root_inode'] > 0, 'report identity')
    require(type(record.get('manifest_bytes')) is int and 0 < record['manifest_bytes'] <= 32768 and
            type(record.get('manifest_sha256')) is str and re.fullmatch(r'[0-9a-f]{64}', record['manifest_sha256']), 'manifest identity')
    started = time.monotonic(); require(math.isfinite(started), 'packet clock')
    deadline = started + 45
    descriptors = []; first = None
    try:
        parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC); descriptors.append(parent)
        for part in path.strip('/').split('/'):
            require(time.monotonic() < deadline, 'packet verification deadline')
            parent = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            descriptors.append(parent)
        root = os.fstat(parent)
        require(stat.S_ISDIR(root.st_mode) and stat.S_IMODE(root.st_mode) == 0o700 and root.st_uid == os.getuid() and
                (root.st_dev, root.st_ino) == (record['root_device'], record['root_inode']), 'report root changed')
        manifest_raw = read_leaf(parent, 'manifest.json', 32768, deadline)
        require(len(manifest_raw) == record['manifest_bytes'] and hashlib.sha256(manifest_raw).hexdigest() == record['manifest_sha256'],
                'manifest mismatch')
        manifest = decode(manifest_raw, 32768)
        require(type(manifest) is dict and set(manifest) == {'schemaVersion', 'files'} and
                type(manifest['schemaVersion']) is int and manifest['schemaVersion'] == 1 and
                type(manifest['files']) is list and 1 <= len(manifest['files']) < MAX_FILES, 'manifest schema')
        expected = {'manifest.json'}; total = len(manifest_raw); outcome = None
        for row in manifest['files']:
            require(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and row['path'] not in expected and
                    type(row['bytes']) is int and 0 <= row['bytes'] <= MAX_TOTAL and
                    type(row['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', row['sha256']), 'manifest row')
            expected.add(row['path']); total += row['bytes']; require(total <= MAX_TOTAL, 'packet bytes')
            data = read_leaf(parent, row['path'], row['bytes'], deadline)
            require(len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], 'payload mismatch')
            if row['path'] == 'outcome.json':
                outcome = decode(data, 1024 * 1024)
        require(type(outcome) is dict and outcome.get('outcome') in ('candidate_pass', 'failed') and
                (record['outcome'] == 'failed' or outcome['outcome'] == 'candidate_pass') and
                outcome.get('runID') == record['runID'] and outcome.get('driverCommit') == record['driverCommit'],
                'packet outcome binding')
        actual = set()
        with os.scandir(parent) as entries:
            for item in entries:
                require(time.monotonic() < deadline, 'packet verification deadline')
                require(len(actual) < MAX_FILES, 'packet entry budget'); actual.add(item.name)
        require(actual == expected and stamp(root) == stamp(os.fstat(parent)) and
                stamp(root) == stamp(os.stat(path, follow_symlinks=False)), 'packet membership/root changed')
    except BaseException as error:
        first = error
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except BaseException:
                first = first or ValueError('packet root close unproved')
    if first is not None:
        raise first
    return path


if __name__ == '__main__':
    # stdout is one validated path only, consumed as data by the fixed template.
    try:
        print(verify_packet(os.environ.get('BUILD_TERMINAL', ''), dict(os.environ)))
    except BaseException:
        raise SystemExit(2)
