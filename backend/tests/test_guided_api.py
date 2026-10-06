from backend import app as api
from backend.guided import GuidedStore, supported
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = GuidedStore(tmp_path / 'state.sqlite', allow_copy=True)
    monkeypatch.setattr(api, '_guided_store', lambda: store)
    return api.app.test_client()


def headers(client):
    session = client.get('/api/guided/session')
    assert session.headers['Cache-Control'] == 'no-store'
    return {'X-Guided-Token': session.json['token']}


def test_guided_session_rejects_cross_origin_and_rebinding(client):
    assert client.get('/api/guided/session', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.get('/api/guided/session', headers={'Host': 'evil.example'}).status_code == 403


def test_guided_rejects_missing_csrf_and_invalid_json(client):
    assert client.post('/api/guided/plans', json={'root': '/tmp'}).status_code == 403
    assert client.post('/api/guided/plans', json=[], headers=headers(client)).status_code == 409


@pytest.mark.skipif(not supported(), reason='POSIX only; unsupported Windows is an explicit product bound')
def test_real_api_scan_apply_recover(client, tmp_path):
    root = tmp_path / 'fixtures'
    root.mkdir()
    (root / 'sample.txt').write_bytes(b'synthetic fixture')
    h = headers(client)
    response = client.post('/api/guided/plans', json={'root': str(root)}, headers=h)
    assert response.status_code == 200
    plan = response.json
    assert plan['state'] == 'preview'
    target = root / plan['actions'][0]['destination']
    assert not target.exists()
    url = '/api/guided/plans/' + plan['id']
    assert client.post(url + '/apply', json={'approved': False}, headers=h).status_code == 409
    result = client.post(url + '/apply', json={'approved': True, 'local_only': True}, headers=h)
    assert result.json['state'] == 'completed'
    assert target.read_bytes() == b'synthetic fixture'
    recovery = client.post(url + '/recover', json={'approved': True}, headers=h)
    assert recovery.status_code == 409
    assert 'disabled' in recovery.json['error']
    assert target.exists()
    assert (root / 'sample.txt').read_bytes() == b'synthetic fixture'
    history = client.get('/api/guided/plans').json
    assert history['plans'][0]['state'] == 'completed'
    assert history['plans'][0]['recovery_available'] is False


def test_default_ui_is_local_guided_workflow(client):
    response = client.get('/ui/')
    assert response.status_code == 200
    content = b' '.join(response.data.split())
    assert b'Read-only preview. Copying is not enabled.' in content
    assert b'Start with a file-type overview' in content
    assert b'This workflow will not apply that layout.' in content
    assert b'id="approve"' not in response.data
    assert b'fonts.googleapis' not in response.data
    assert b'nav-recycle' not in response.data


def test_legacy_backup_delete_retains_history_when_trash_unavailable(tmp_path, monkeypatch):
    from backend import op_store
    monkeypatch.setattr(op_store, 'DB_FILE', str(tmp_path / 'legacy.sqlite'))
    monkeypatch.setattr(op_store, 'BACKUP_ROOT', str(tmp_path / 'backups'))
    monkeypatch.setattr(op_store, 'send2trash', None)
    source = tmp_path / 'original.txt'
    source.write_text('must survive')
    plan = op_store.create_op([])
    backup = op_store.backup_file(plan['id'], str(source))
    with pytest.raises(OSError, match='retained'):
        op_store.delete_op(plan['id'])
    assert op_store.get_op(plan['id'])
    assert __import__('pathlib').Path(backup).read_text() == 'must survive'
    with pytest.raises(OSError, match='retained'):
        op_store.cleanup_recycle(0)
    assert __import__('pathlib').Path(backup).exists()


def test_legacy_failed_trash_does_not_fall_back_to_delete(tmp_path, monkeypatch):
    from backend import op_store
    monkeypatch.setattr(op_store, 'DB_FILE', str(tmp_path / 'legacy.sqlite'))
    monkeypatch.setattr(op_store, 'BACKUP_ROOT', str(tmp_path / 'backups'))

    def fail(_):
        raise OSError('trash unavailable on volume')
    monkeypatch.setattr(op_store, 'send2trash', fail)
    source = tmp_path / 'original.txt'
    source.write_text('must survive')
    plan = op_store.create_op([])
    backup = op_store.backup_file(plan['id'], str(source))
    with pytest.raises(OSError):
        op_store.delete_op(plan['id'])
    assert op_store.get_op(plan['id'])
    assert __import__('pathlib').Path(backup).read_text() == 'must survive'


def test_legacy_routes_also_reject_cross_origin_filesystem_access(client):
    response = client.post('/api/duplicates', json={}, headers={'Origin': 'https://evil.example'})
    assert response.status_code == 403
    response = client.post('/api/organise/execute', json={}, headers={'Host': 'evil.example'})
    assert response.status_code == 403


def test_all_ui_pages_disallow_clickjacking(client):
    for path in ['/ui/', '/ui/index.html']:
        response = client.get(path)
        assert response.headers['X-Frame-Options'] == 'DENY'
        assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']


def test_default_capabilities_and_apply_are_read_only(tmp_path, monkeypatch):
    from unittest import mock
    from backend import guided
    store = GuidedStore(tmp_path / 'read-only-state.sqlite')
    monkeypatch.setattr(api, '_guided_store', lambda: store)
    client = api.app.test_client()
    response = client.get('/api/guided/session')
    capabilities = response.json['capabilities']
    assert capabilities['mode'] == 'read_only'
    assert capabilities['copy_apply']['enabled'] is False
    assert capabilities['recovery']['enabled'] is False
    assert capabilities['remote_inference']['enabled'] is False
    assert capabilities['disk_model']['status'] == 'not_implemented'
    with mock.patch.object(guided, 'open_root') as roots:
        response = client.post('/api/guided/plans/' + 'a' * 32 + '/apply',
                               json={'approved': True, 'local_only': True},
                               headers={'X-Guided-Token': response.json['token']})
        assert response.status_code == 409
        assert 'Read-only' in response.json['error']
        roots.assert_not_called()
    assert client.get('/api/guided/plans').json['capabilities']['mode'] == 'read_only'


@pytest.mark.parametrize('path', ['/api/organise/execute', '/api/organise/undo',
                                  '/api/recycle/cleanup', '/api/recycle/delete_op'])
def test_legacy_mutation_routes_are_disabled_by_default(client, monkeypatch, path):
    from unittest import mock
    monkeypatch.delenv('DISK_ORGANISER_ENABLE_LEGACY_MUTATIONS', raising=False)
    with mock.patch.object(api, 'get_op') as get_op, \
            mock.patch.object(api, 'cleanup_recycle') as cleanup, \
            mock.patch.object(api, 'delete_op') as delete:
        response = client.post(path, json={'op_id': 'synthetic-id', 'dry_run': 'true'})
        assert response.status_code == 409
        assert 'Read-only' in response.json['error']
        get_op.assert_not_called()
        cleanup.assert_not_called()
        delete.assert_not_called()
