"""Benign data-only journal corruption tests; no path-redirection operations.

Invalid path strings below are passed only to the pure validator. Integration
checks use ordinary temporary app state and mock selected-folder I/O, so they
establish rejection before any file operation rather than reproduce an escape.
"""
import copy
import json
import stat
from unittest import mock

import pytest

from backend import guided, guided_schema as schema


def sample():
    plan_id = 'a' * 32
    fp = {'stamp': [1, 10, 3, 100, 100, stat.S_IFREG | 0o600], 'sha256': 'b' * 64, 'size': 3}
    return {
        'schema_version': 1, 'id': plan_id, 'root': '/synthetic/folder', 'root_identity': [1, 5],
        'output': schema.output_for(plan_id), 'state': 'preview', 'created': 1000.0,
        'actions': [{'source': 'note.txt', 'category': 'Documents',
                     'destination': schema.destination_for(plan_id, 'note.txt'),
                     'reason': '.txt extension → Documents; content is not interpreted',
                     'fingerprint': fp, 'state': 'planned', 'owned': None}],
        'skipped': [], 'directories': {}, 'limitations': 'Synthetic validator fixture',
        'bytes': 3, 'required_bytes': 3 + schema.RESERVE_BYTES, 'error': None,
    }


def test_valid_schema_round_trip_is_data_only():
    p = sample()
    with mock.patch.object(guided, 'open_root') as roots:
        assert schema.decode(schema.canonical(p), p['id']) == p
        roots.assert_not_called()


@pytest.mark.parametrize('field,value', [
    ('schema_version', None), ('schema_version', True), ('schema_version', 99),
    ('id', 'invalid'), ('id', []), ('output', 'unexpected-output'), ('output', None),
    ('root', 'relative'), ('root', '/'), ('root', '/synthetic/./folder'),
    ('root', '/synthetic//folder'), ('root', '/synthetic/folder/'),
    ('root_identity', [True, 5]), ('root_identity', [1]),
    ('created', float('nan')), ('created', float('inf')), ('created', True),
    ('state', 'unknown'), ('state', []), ('actions', {}), ('skipped', {}),
    ('directories', {'Unknown': [1, 30]}), ('bytes', False), ('bytes', 2),
    ('required_bytes', 0), ('limitations', []), ('error', {}),
])
def test_rejects_corrupt_top_level_fields_without_io(field, value):
    p = sample()
    p[field] = value
    with pytest.raises(schema.JournalError):
        schema.validate(p)


@pytest.mark.parametrize('field,value', [
    ('source', ''), ('source', '.'), ('source', '..'), ('source', 'nested/note.txt'),
    ('source', 'nested\\note.txt'), ('source', '\x00note.txt'), ('source', '.hidden.txt'),
    ('category', 'Images'), ('category', '.'), ('category', []),
    ('destination', 'unexpected-destination'), ('destination', None),
    ('reason', 'Altered reason'), ('fingerprint', {}), ('state', 'unknown'),
    ('owned', [1, 10]), ('owned', [False, 10]),
])
def test_rejects_corrupt_action_fields_without_io(field, value):
    p = sample()
    p['actions'][0][field] = value
    with pytest.raises(schema.JournalError):
        schema.validate(p)


def test_exact_keys_row_id_and_derived_paths_required():
    for mutate in [lambda p: p.update(extra=True), lambda p: p.pop('schema_version'),
                   lambda p: p['actions'][0].update(extra=True)]:
        p = sample()
        mutate(p)
        with pytest.raises(schema.JournalError):
            schema.validate(p)
    p = sample()
    with pytest.raises(schema.JournalError):
        schema.decode(json.dumps(p), 'c' * 32)
    with pytest.raises(schema.JournalError):
        schema.decode('{"id":"a","id":"a"}', 'a')
    with pytest.raises(schema.JournalError):
        schema.decode('not-json', p['id'])


def test_rejects_duplicate_sources_and_original_ownership_claims():
    p = sample()
    p['actions'].append(copy.deepcopy(p['actions'][0]))
    p['bytes'] *= 2
    p['required_bytes'] = p['bytes'] + schema.RESERVE_BYTES
    with pytest.raises(schema.JournalError):
        schema.validate(p)
    p = sample()
    p['state'] = 'applying'
    p['directories'] = {'.': [1, 20], 'Documents': [1, 21]}
    p['actions'][0].update(state='copying', owned=[1, 10])
    with pytest.raises(schema.JournalError):
        schema.validate(p)
    p['actions'][0]['owned'] = [1, 20]
    with pytest.raises(schema.JournalError):
        schema.validate(p)
    p['actions'][0]['owned'] = [1, 30]
    p['directories']['Documents'] = [1, 10]
    with pytest.raises(schema.JournalError):
        schema.validate(p)


def test_completed_requires_all_consistent_results():
    p = sample()
    p['state'] = 'completed'
    with pytest.raises(schema.JournalError):
        schema.validate(p)
    p['directories'] = {'.': [1, 20], 'Documents': [1, 21]}
    a = p['actions'][0]
    a.update(state='copied', owned=[1, 30], result_fingerprint=copy.deepcopy(a['fingerprint']))
    a['result_fingerprint']['stamp'][1] = 30
    schema.validate(p)
    a['result_fingerprint']['sha256'] = 'c' * 64
    with pytest.raises(schema.JournalError):
        schema.validate(p)


@pytest.mark.skipif(not guided.supported(), reason='POSIX guided operations only')
def test_restart_and_structurally_valid_alteration_cannot_authorise_apply(tmp_path):
    root = tmp_path / 'ordinary-fixture'
    root.mkdir()
    (root / 'note.txt').write_text('fixture')
    store = guided.GuidedStore(tmp_path / 'app-state.sqlite', allow_copy=True)
    p = store.scan(str(root))
    assert store.describe(p)['can_apply'] is True
    altered = copy.deepcopy(p)
    altered['created'] += 0.25  # Benign scalar edit; not a filesystem-redirection test.
    schema.validate(altered)
    with store.connection() as con:
        con.execute('UPDATE guided SET payload=? WHERE id=?', (json.dumps(altered), p['id']))
    with mock.patch.object(guided, 'open_root') as roots:
        with pytest.raises(guided.GuidedError, match='authorisation'):
            store.apply(p['id'], True, True)
        roots.assert_not_called()
    store.save(p)
    guided._TRUSTED_PREVIEWS.pop(store._preview_key(p['id']))
    with mock.patch.object(guided, 'open_root') as roots:
        with pytest.raises(guided.GuidedError, match='authorisation'):
            guided.GuidedStore(store.db_path, allow_copy=True).apply(p['id'], True, True)
        roots.assert_not_called()
    assert sorted(x.name for x in root.iterdir()) == ['note.txt']


def test_malformed_and_old_journals_are_retained_and_never_executed(tmp_path):
    store = guided.GuidedStore(tmp_path / 'app-state.sqlite', allow_copy=True)
    payload = '{"unexpected": true}'
    plan_id = 'd' * 32
    with store.connection() as con:
        con.execute('INSERT INTO guided VALUES (?,?)', (plan_id, payload))
    with mock.patch.object(guided, 'open_root') as roots, \
            mock.patch.object(guided.os, 'unlink') as unlink, \
            mock.patch.object(guided.os, 'rmdir') as rmdir:
        with pytest.raises(schema.JournalError):
            store.get(plan_id)
        with pytest.raises(schema.JournalError):
            store.recover(plan_id, True)
        history = store.history()
        assert history['plans'] == [] and history['blocked_records'] == 1
        roots.assert_not_called()
        unlink.assert_not_called()
        rmdir.assert_not_called()
    with store.connection() as con:
        assert con.execute('SELECT payload FROM guided WHERE id=?', (plan_id,)).fetchone()[0] == payload
