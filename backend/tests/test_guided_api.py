from backend import app as api
from backend.guided import GuidedStore, supported
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = GuidedStore(tmp_path / 'state.sqlite')
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
    assert client.post(url + '/recover', json={'approved': True}, headers=h).json['state'] == 'undone'
    assert not target.exists()
    assert (root / 'sample.txt').read_bytes() == b'synthetic fixture'
    assert client.get('/api/guided/plans').json['plans'][0]['state'] == 'undone'


def test_default_ui_is_local_guided_workflow(client):
    response = client.get('/ui/')
    assert response.status_code == 200
    assert b'Guided copies' in response.data
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
