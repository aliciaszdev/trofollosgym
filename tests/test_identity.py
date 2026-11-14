import re
import time
import uuid
import pytest
from trofollos.app import create_app, connect, digest, HASHER

@pytest.fixture
def setup(tmp_path):
    path = tmp_path / 'isolated.sqlite3'
    config = {'TESTING': True, 'DATABASE': str(path), 'AREA': 'admin'}
    app = create_app(config)
    with connect(path) as db:
        for name, role in [('owner','TOP'), ('alice','normal'), ('bob','normal')]:
            db.execute('INSERT INTO users(id,username,role,password_hash,created_at) VALUES (?,?,?,?,?)', (name, name, role, HASHER.hash('A strong password 123!'), int(time.time())))
    return app, path

def csrf(client):
    response = client.get('/login')
    # First response installs the CSRF cookie; the next renders it.
    response = client.get('/login')
    return re.search(r'name="csrf" value="([^"]+)"', response.text).group(1)

def login(client, name='owner'):
    return client.post('/login', data={'csrf': csrf(client), 'username': name, 'password': 'A strong password 123!'})

def token(client):
    return re.search(r'name="csrf" value="([^"]+)"', client.get('/profile').text).group(1)

def test_access_control_and_no_private_exports(setup):
    app, path = setup
    c = app.test_client()
    assert c.get('/api/me').status_code == 401
    assert login(c, 'alice').status_code == 302
    assert c.get('/admin').status_code == 403
    assert c.post('/admin/users', data={'csrf':token(c), 'username':'other', 'role':'TOP'}).status_code == 403
    assert c.get('/api/me').json['id'] == 'alice'
    assert c.get('/api/users/bob').status_code == 404
    assert c.get('/api/measurements/bob').status_code == 404
    assert c.get('/api/private-notes/bob').status_code == 404
    assert c.post('/logout', data={'csrf':token(c)}).status_code == 302
    login(c)
    assert c.get('/admin').status_code == 200
    assert c.get('/api/measurements/alice').status_code == 404
    assert set(c.get('/api/me').json) == {'id','username','role'}

def test_create_activate_reset_and_persistence(setup):
    app, path = setup
    top = app.test_client(); login(top)
    r = top.post('/admin/users', data={'csrf':token(top), 'username':'new.user', 'role':'normal'})
    assert r.status_code == 200
    code = re.search(r'<code class="token">([^<]+)', r.text).group(1)
    c = app.test_client(); csrf(c)
    r = c.post('/activate', data={'csrf':csrf(c), 'token':code, 'password':'A strong password 123!', 'confirm':'A strong password 123!'})
    assert r.status_code == 200
    assert c.post('/activate', data={'csrf':csrf(c), 'token':code, 'password':'A strong password 123!', 'confirm':'A strong password 123!'}).status_code == 400
    login(c, 'new.user')
    uid = c.get('/api/me').json['id']
    # Independent application instance reads persisted identity and shared session.
    second = create_app({'TESTING':True,'DATABASE':str(path),'AREA':'training'})
    c2 = second.test_client(); c2.set_cookie('trof_session', c.get_cookie('trof_session').value)
    assert c2.get('/api/me').json['id'] == uid
    assert c2.get('/admin').status_code == 404
    r = top.post('/admin/users/'+uid, data={'csrf':token(top),'action':'reset','confirm':'yes'})
    assert r.status_code == 200
    assert c.get('/api/me').status_code == 401
    assert c2.get('/api/me').status_code == 401
    with connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 4
        assert db.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()[0] is None
        assert code not in str([tuple(x) for x in db.execute('SELECT * FROM invitations')])

def test_last_top_csrf_and_duplicates(setup):
    app, path = setup
    c = app.test_client(); login(c)
    assert c.post('/admin/users', data={'username':'x','role':'TOP'}).status_code == 400
    for action in ('disable','normal'):
        assert c.post('/admin/users/owner', data={'csrf':token(c),'action':action,'confirm':'yes'}).status_code == 409
    assert c.post('/admin/users',data={'csrf':token(c),'username':'ALICE','role':'normal'}).status_code == 409
    assert c.post('/admin/users/alice',data={'csrf':token(c),'action':'disable'}).status_code == 400
    assert c.post('/admin/users/alice',data={'csrf':token(c),'action':'disable','confirm':'yes'}).status_code == 302
    other = app.test_client()
    assert login(other,'alice').status_code == 401

def test_rate_limit_and_cookie_security(setup):
    app,path = setup
    c = app.test_client()
    for _ in range(5):
        assert c.post('/login',data={'csrf':csrf(c),'username':'alice','password':'wrong'}).status_code == 401
    assert login(c,'alice').status_code == 429
    prod = create_app({'TESTING':True,'DATABASE':str(path),'AREA':'admin','PRODUCTION':True})
    r = prod.test_client().get('/login')
    assert 'Secure' in r.headers['Set-Cookie']
    assert 'HttpOnly' in r.headers['Set-Cookie']
    assert 'frame-ancestors' in r.headers['Content-Security-Policy']
    assert r.headers['Cache-Control'] == 'no-store'

def test_password_change_revokes_all_sessions(setup):
    app,path = setup
    c = app.test_client(); login(c,'alice')
    other = app.test_client(); login(other,'alice')
    assert c.post('/profile', data={'csrf':token(c),'old_password':'A strong password 123!','password':'Another strong password!','confirm':'Another strong password!'}).status_code == 302
    assert other.get('/api/me').status_code == 401
    assert c.get('/api/me').status_code == 401

def test_backup_restore_without_overwrite(setup, tmp_path):
    from trofollos.database import copy_database
    app,path=setup
    backup=tmp_path/'backup.sqlite3'
    restored=tmp_path/'restored.sqlite3'
    copy_database(path,backup)
    copy_database(backup,restored)
    with connect(restored) as db:
        assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 3
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    with pytest.raises(FileExistsError):
        copy_database(backup,path)


def test_first_page_csrf_and_expired_invitation(setup):
    app,path=setup
    c=app.test_client()
    r=c.get('/login')
    value=re.search(r'name="csrf" value="([^"]+)"',r.text).group(1)
    assert c.post('/login',data={'csrf':value,'username':'alice','password':'A strong password 123!'}).status_code == 302
    top=app.test_client(); login(top)
    r=top.post('/admin/users',data={'csrf':token(top),'username':'expired','role':'normal'})
    code=re.search(r'<code class="token">([^<]+)',r.text).group(1)
    with connect(path) as db:
        db.execute('UPDATE invitations SET expires_at=0')
    other=app.test_client()
    assert other.post('/activate',data={'csrf':csrf(other),'token':code,'password':'Long enough password','confirm':'Long enough password'}).status_code == 400

def test_migration_is_repeatable_and_concurrent(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from trofollos.app import initialize
    path=tmp_path/'migration.sqlite3'
    # Establish WAL before exercising serialized concurrent migration inspection.
    initialize(path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: initialize(path), range(2)))
    with connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0] == 2
