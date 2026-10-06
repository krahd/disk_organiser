"""Pure validation of untrusted guided journals; performs no filesystem calls."""
from __future__ import annotations

import json
import math
import re
import stat
from pathlib import PurePosixPath

SCHEMA_VERSION = 1
MAX_FILES = 500
MAX_BYTES = 1024 ** 3
RESERVE_BYTES = 16 * 1024 ** 2
MAX_JOURNAL_CHARS = 2 * 1024 ** 2
CATEGORIES = {
    'Documents': {'.pdf', '.txt', '.md', '.docx', '.odt', '.csv', '.xlsx'},
    'Images': {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.heic'},
    'Audio': {'.wav', '.mp3', '.aiff', '.flac', '.m4a', '.ogg'},
    'Video': {'.mp4', '.mov', '.mkv', '.webm'},
    'Archives': {'.zip', '.tar', '.gz', '.7z'},
}


class JournalError(ValueError):
    """The journal is incomplete, unsupported or inconsistent; retain it."""


def require(condition):
    if not condition:
        raise JournalError('Journal integrity could not be established. '
                           'No file operation is permitted; retain the journal.')


def leaf(value, hidden=False):
    require(type(value) is str and 0 < len(value) <= 255)
    require(value not in {'.', '..'} and not any(c in value for c in ('/', '\\', '\x00')))
    require(hidden or not value.startswith('.'))
    return value


def category_for(source):
    suffix = PurePosixPath(source).suffix.casefold()
    return next((key for key, suffixes in CATEGORIES.items() if suffix in suffixes), None)


def output_for(plan_id):
    require(type(plan_id) is str and re.fullmatch('[0-9a-f]{32}', plan_id) is not None)
    return 'Organised-' + plan_id[:12]


def destination_for(plan_id, source):
    leaf(source)
    category = category_for(source)
    require(category is not None)
    return f'{output_for(plan_id)}/{category}/{source}'


def root_path(value):
    require(type(value) is str and 1 < len(value) <= 4096)
    require(value.startswith('/') and not value.startswith('//'))
    require('\x00' not in value and '\\' not in value)
    parts = value.split('/')[1:]
    require(all(part and part not in {'.', '..'} for part in parts))
    require(str(PurePosixPath(value)) == value)


def integer(value, minimum=0, maximum=2 ** 127):
    require(type(value) is int and minimum <= value <= maximum)


def ident(value):
    require(type(value) is list and len(value) == 2)
    integer(value[0])
    integer(value[1], 1)
    return tuple(value)


def fingerprint(value, device):
    require(type(value) is dict and set(value) == {'stamp', 'sha256', 'size'})
    integer(value['size'], maximum=MAX_BYTES)
    require(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']) is not None)
    s = value['stamp']
    require(type(s) is list and len(s) == 6)
    for field in [*s[:3], s[5]]:
        integer(field)
    for timestamp in s[3:5]:
        integer(timestamp, minimum=-(2 ** 127))
    require(s[0] == device and s[1] > 0 and s[2] == value['size'])
    require(s[5] <= 2 ** 32 and stat.S_ISREG(s[5]))
    return tuple(s[:2])


def _validate(plan, expected_id=None):
    """Validate every persisted field and every derived relationship, without I/O.

    Structural validation does not authenticate ownership or user authorisation.
    Callers must separately require a fresh in-process preview before applying.
    A journal alone must never authorise deleting a file.
    """
    fields = {'schema_version', 'id', 'root', 'root_identity', 'output', 'state', 'created',
              'actions', 'skipped', 'directories', 'limitations', 'bytes', 'required_bytes', 'error'}
    require(type(plan) is dict and set(plan) == fields)
    require(type(plan['schema_version']) is int and plan['schema_version'] == SCHEMA_VERSION)
    require(plan['output'] == output_for(plan['id']))
    require(expected_id is None or plan['id'] == expected_id)
    root_path(plan['root'])
    root = ident(plan['root_identity'])
    require(type(plan['state']) is str and plan['state'] in {'preview', 'applying', 'completed', 'interrupted'})
    require(type(plan['created']) in {int, float} and 0 < plan['created'] <= 2 ** 53 and math.isfinite(plan['created']))
    require(type(plan['limitations']) is str and len(plan['limitations']) <= 4096)
    require(plan['error'] is None or (type(plan['error']) is str and len(plan['error']) <= 16384))
    actions, skipped, directories = plan['actions'], plan['skipped'], plan['directories']
    require(type(actions) is list and type(skipped) is list and len(actions) + len(skipped) <= MAX_FILES)
    require(type(directories) is dict and set(directories) <= {'.', *CATEGORIES})
    sources, source_ids, owned_ids, categories = set(), set(), set(), set()
    size = 0
    for action in actions:
        required = {'source', 'category', 'destination', 'reason', 'fingerprint', 'state', 'owned'}
        require(type(action) is dict and required <= set(action) <= required | {'result_fingerprint'})
        source = leaf(action['source'])
        require(source.casefold() not in sources)
        sources.add(source.casefold())
        category = category_for(source)
        require(category is not None and action['category'] == category)
        categories.add(category)
        require(action['destination'] == destination_for(plan['id'], source))
        reason = f'{PurePosixPath(source).suffix.casefold()} extension → {category}; content is not interpreted'
        require(action['reason'] == reason)
        source_id = fingerprint(action['fingerprint'], root[0])
        require(source_id not in source_ids and source_id != root)
        source_ids.add(source_id)
        size += action['fingerprint']['size']
        require(type(action['state']) is str and action['state'] in {'planned', 'copying', 'copied'})
        if action['owned'] is not None:
            owned = ident(action['owned'])
            require(owned[0] == root[0] and owned not in owned_ids)
            owned_ids.add(owned)
        if action['state'] == 'planned':
            require(action['owned'] is None and 'result_fingerprint' not in action)
        else:
            require(action['owned'] is not None)
        if action['state'] == 'copied':
            require('result_fingerprint' in action)
        if 'result_fingerprint' in action:
            require(action['state'] == 'copied')
            result = action['result_fingerprint']
            require(fingerprint(result, root[0]) == tuple(action['owned']))
            require(result['size'] == action['fingerprint']['size'])
            require(result['sha256'] == action['fingerprint']['sha256'])
        if plan['state'] == 'preview':
            require(action['state'] == 'planned')
        if plan['state'] == 'completed':
            require(action['state'] == 'copied')
    for entry in skipped:
        require(type(entry) is dict and set(entry) == {'path', 'reason'})
        leaf(entry['path'], hidden=True)
        require(type(entry['reason']) is str and len(entry['reason']) <= 16384)
        require(entry['path'].casefold() not in sources)
        sources.add(entry['path'].casefold())
    integer(plan['bytes'], maximum=MAX_BYTES)
    integer(plan['required_bytes'], maximum=MAX_BYTES + RESERVE_BYTES)
    require(plan['bytes'] == size and plan['required_bytes'] == size + RESERVE_BYTES)
    require(set(directories) <= {'.', *categories})
    dir_ids = [ident(value) for value in directories.values()]
    require(all(value[0] == root[0] for value in dir_ids))
    require(len(set(dir_ids)) == len(dir_ids))
    require(not (source_ids & owned_ids or set(dir_ids) & source_ids or set(dir_ids) & owned_ids))
    require(root not in owned_ids and root not in dir_ids)
    if directories:
        require('.' in directories)
    if plan['state'] == 'preview':
        require(not directories and plan['error'] is None)
    if plan['state'] == 'completed':
        require(bool(actions) and set(directories) == {'.', *categories} and plan['error'] is None)
    for action in actions:
        if action['owned'] is not None:
            require('.' in directories and action['category'] in directories)
    return plan


def validate(plan, expected_id=None):
    try:
        return _validate(plan, expected_id)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        raise JournalError('Journal integrity could not be established. '
                           'Retain the journal and scan again.') from exc


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def decode(payload, expected_id):
    require(type(payload) is str and len(payload) <= MAX_JOURNAL_CHARS)
    try:
        plan = json.loads(payload, object_pairs_hook=_unique_object,
                          parse_constant=lambda _: require(False))
        return validate(plan, expected_id)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        raise JournalError('Journal integrity could not be established. Retain the journal and scan again.') from exc


def canonical(plan):
    validate(plan)
    return json.dumps(plan, sort_keys=True, separators=(',', ':'), allow_nan=False)
