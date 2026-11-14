"""TrofollosGym: identidad compartida, consola y entrenamiento independientes."""
import argparse
import functools
import hashlib
import os
import re
import secrets
import sqlite3
import time
import uuid
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for

HASHER = PasswordHasher()
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))
ROOT = Path(__file__).resolve().parent.parent


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def connect(path):
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=15000')
    return db


def initialize(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('BEGIN IMMEDIATE')
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='schema_migrations'").fetchone()
        if not exists:
            for statement in (ROOT / 'migrations/001_identity.sql').read_text(encoding='utf-8-sig').split(';'):
                if statement.strip():
                    db.execute(statement)
        version = db.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        if version > 2:
            raise RuntimeError('Versión de base de datos no compatible')
        if version < 2:
            for statement in (ROOT / 'migrations/002_catalog_routines.sql').read_text(encoding='utf-8-sig').split(';'):
                if statement.strip():
                    db.execute(statement)


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(DATABASE=os.environ.get('TROF_DATABASE', str(ROOT / '.runtime/development/identity.sqlite3')),
                      AREA=os.environ.get('TROF_AREA', 'training'),
                      PRODUCTION=os.environ.get('TROF_ENV') == 'production', MAX_CONTENT_LENGTH=16384,
                      TRAINING_URL=os.environ.get('TROF_TRAINING_URL','http://127.0.0.1:8080/'),
                      ADMIN_URL=os.environ.get('TROF_ADMIN_URL','http://127.0.0.1:8081/admin'))
    app.config.update(config or {})
    if app.config['AREA'] not in ('training', 'admin'):
        raise RuntimeError('Área no válida')
    if app.config['PRODUCTION'] and not (config and config.get('DATABASE')) and not os.environ.get('TROF_DATABASE'):
        raise RuntimeError('Producción requiere TROF_DATABASE externo')
    initialize(app.config['DATABASE'])

    def db():
        if 'db' not in g:
            g.db = connect(app.config['DATABASE'])
        return g.db

    @app.teardown_appcontext
    def close_db(error):
        if 'db' in g:
            g.db.close()

    def audit(action, target):
        db().execute('INSERT INTO audit VALUES (?,?,?,?,?)',
                     (str(uuid.uuid4()), g.user['id'] if g.user else None, action, target, int(time.time())))

    def csrf():
        if g.auth:
            return g.auth['csrf']
        return request.cookies.get('trof_csrf', '') or getattr(g, 'anonymous_csrf', '')

    @app.before_request
    def security():
        g.user = g.auth = None
        g.anonymous_csrf = secrets.token_urlsafe(32)
        token = request.cookies.get('trof_session', '')
        if token:
            g.auth = db().execute('SELECT * FROM sessions WHERE token_hash=? AND expires_at>?', (digest(token), time.time())).fetchone()
            if g.auth:
                g.user = db().execute('SELECT * FROM users WHERE id=? AND active=1', (g.auth['user_id'],)).fetchone()
                if not g.user:
                    g.auth = None
        if request.method == 'POST':
            expected = csrf()
            supplied = request.form.get('csrf', '') or request.headers.get('X-CSRF-Token', '')
            if not expected or not secrets.compare_digest(expected, supplied):
                abort(400, 'Formulario caducado. Recarga la página.')

    @app.after_request
    def headers(response):
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer',
                                 'Content-Security-Policy': "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"})
        if app.config['PRODUCTION']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        if not request.cookies.get('trof_csrf'):
            response.set_cookie('trof_csrf', g.anonymous_csrf, secure=app.config['PRODUCTION'], httponly=True, samesite='Strict')
        return response

    def protected(top=False):
        def decorator(fn):
            @functools.wraps(fn)
            def wrapped(*args, **kwargs):
                if not g.user:
                    if request.path.startswith('/api/'):
                        abort(401)
                    return redirect(url_for('login'))
                if top and g.user['role'] != 'TOP':
                    abort(403)
                return fn(*args, **kwargs)
            return wrapped
        return decorator

    @app.context_processor
    def context():
        return dict(user=g.user, csrf=csrf(), area=app.config['AREA'], training_url=app.config['TRAINING_URL'], admin_url=app.config['ADMIN_URL'])

    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(429)
    def error(err):
        if request.path.startswith('/api/'):
            return jsonify(error=err.description), err.code
        return render_template('page.html', page='error', message=err.description), err.code

    @app.get('/health')
    def health():
        db().execute('SELECT 1').fetchone()
        return jsonify(status='ok', area=app.config['AREA'])

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()[:64]
            password = request.form.get('password', '')[:1024]
            now = int(time.time())
            scopes = ['ip:' + digest(request.remote_addr or ''), 'user:' + digest(username.casefold())]
            # Transaction serializes counters across the two independent processes.
            db().execute('BEGIN IMMEDIATE')
            for scope in scopes:
                entry = db().execute('SELECT * FROM login_attempts WHERE scope=?', (scope,)).fetchone()
                if entry and entry['reset_at'] > now and entry['failures'] >= 5:
                    db().rollback()
                    abort(429, 'Demasiados intentos. Espera 15 minutos.')
            u = db().execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
            valid = False
            try:
                HASHER.verify(u['password_hash'] if u and u['password_hash'] else DUMMY_HASH, password)
                valid = bool(u and u['active'] and u['password_hash'])
            except (VerificationError, InvalidHashError):
                pass
            if not valid:
                for scope in scopes:
                    db().execute('INSERT INTO login_attempts VALUES (?,1,?) ON CONFLICT(scope) DO UPDATE SET failures=CASE WHEN reset_at<=? THEN 1 ELSE failures+1 END, reset_at=CASE WHEN reset_at<=? THEN ? ELSE reset_at END', (scope, now+900, now, now, now+900))
                db().commit()
                abort(401, 'Usuario o contraseña incorrectos.')
            if HASHER.check_needs_rehash(u['password_hash']):
                db().execute('UPDATE users SET password_hash=? WHERE id=?', (HASHER.hash(password), u['id']))
            db().executemany('DELETE FROM login_attempts WHERE scope=?', [(s,) for s in scopes])
            token = secrets.token_urlsafe(48)
            db().execute('DELETE FROM sessions WHERE expires_at<=?', (now,))
            db().execute('INSERT INTO sessions VALUES (?,?,?,?)', (digest(token), u['id'], secrets.token_urlsafe(32), now+43200))
            db().commit()
            response = redirect(url_for('home'))
            response.set_cookie('trof_session', token, max_age=43200, secure=app.config['PRODUCTION'], httponly=True, samesite='Strict')
            return response
        return render_template('page.html', page='login')

    @app.post('/logout')
    @protected()
    def logout():
        db().execute('DELETE FROM sessions WHERE token_hash=?', (digest(request.cookies.get('trof_session', '')),))
        db().commit()
        response = redirect(url_for('login'))
        response.delete_cookie('trof_session')
        return response

    @app.route('/activate', methods=['GET', 'POST'])
    def activate():
        # Token travels in the form, never in a URL or access log.
        if request.method == 'POST':
            token = request.form.get('token', '').strip()
            password = request.form.get('password', '')
            if len(password) < 12 or len(password) > 256:
                abort(400, 'Usa una contraseña de entre 12 y 256 caracteres.')
            if password != request.form.get('confirm'):
                abort(400, 'Las contraseñas no coinciden.')
            hashed = HASHER.hash(password)
            db().execute('BEGIN IMMEDIATE')
            invite = db().execute('SELECT i.* FROM invitations i JOIN users u ON u.id=i.user_id WHERE i.token_hash=? AND i.expires_at>? AND u.active=1', (digest(token), time.time())).fetchone()
            if not invite:
                db().rollback()
                abort(400, 'Código no válido o caducado.')
            db().execute('UPDATE users SET password_hash=?,revision=revision+1 WHERE id=?', (hashed, invite['user_id']))
            db().execute('DELETE FROM invitations WHERE user_id=?', (invite['user_id'],))
            db().execute('DELETE FROM sessions WHERE user_id=?', (invite['user_id'],))
            audit('access_established', invite['user_id'])
            db().commit()
            return render_template('page.html', page='message', message='Contraseña establecida. Ya puedes iniciar sesión.')
        return render_template('page.html', page='activate')

    @app.get('/')
    @protected()
    def home():
        if app.config['AREA'] == 'admin':
            if g.user['role'] != 'TOP':
                abort(403)
            return redirect(url_for('admin'))
        return render_template('page.html', page='home')

    @app.get('/api/me')
    @protected()
    def me():
        return jsonify(id=g.user['id'], username=g.user['username'], role=g.user['role'])

    @app.route('/profile', methods=['GET', 'POST'])
    @protected()
    def profile():
        if request.method == 'POST':
            old = request.form.get('old_password', '')
            password = request.form.get('password', '')
            try:
                HASHER.verify(g.user['password_hash'], old)
            except VerificationError:
                abort(400, 'Contraseña actual incorrecta.')
            if not 12 <= len(password) <= 256 or password != request.form.get('confirm'):
                abort(400, 'Revisa la nueva contraseña y su confirmación (12–256 caracteres).')
            db().execute('UPDATE users SET password_hash=? WHERE id=?', (HASHER.hash(password), g.user['id']))
            db().execute('DELETE FROM sessions WHERE user_id=?', (g.user['id'],))
            audit('password_changed', g.user['id'])
            db().commit()
            return redirect(url_for('login'))
        return render_template('page.html', page='profile')

    def admin_area(fn):
        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            if app.config['AREA'] != 'admin':
                abort(404)
            return fn(*args, **kwargs)
        return wrapped

    @app.get('/admin')
    @admin_area
    @protected(top=True)
    def admin():
        users = db().execute('SELECT id,username,role,active FROM users ORDER BY username').fetchall()
        audit_rows = db().execute('SELECT action,created_at FROM audit ORDER BY created_at DESC LIMIT 20').fetchall()
        return render_template('page.html', page='admin', users=users, audit_rows=audit_rows)

    @app.post('/admin/users')
    @admin_area
    @protected(top=True)
    def create_user():
        username = request.form.get('username', '').strip()
        role = request.form.get('role')
        if not re.fullmatch(r'[A-Za-z0-9_.-]{3,64}', username) or role not in ('TOP', 'normal'):
            abort(400, 'Usuario: 3–64 letras, números, puntos, guiones o guiones bajos. Revisa el perfil.')
        uid = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        try:
            with db():
                db().execute('INSERT INTO users (id,username,role,created_at) VALUES (?,?,?,?)', (uid, username, role, int(time.time())))
                db().execute('INSERT INTO invitations VALUES (?,?,?)', (digest(token), uid, int(time.time())+86400))
                audit('user_created', uid)
        except sqlite3.IntegrityError:
            abort(409, 'Ese nombre de usuario ya existe.')
        return render_template('page.html', page='invitation', token=token, username=username)

    @app.post('/admin/users/<uid>')
    @admin_area
    @protected(top=True)
    def update_user(uid):
        action = request.form.get('action')
        if request.form.get('confirm') != 'yes':
            abort(400, 'Confirma explícitamente la operación.')
        db().execute('BEGIN IMMEDIATE')
        target = db().execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
        if not target:
            abort(404)
        if action in ('disable', 'normal') and target['active'] and target['role'] == 'TOP':
            count = db().execute("SELECT COUNT(*) FROM users WHERE active=1 AND role='TOP'").fetchone()[0]
            if count <= 1:
                db().rollback()
                abort(409, 'Debe quedar al menos una cuenta TOP activa.')
        if action == 'normal' and target['role'] == 'TOP':
            shared = db().execute("SELECT 1 FROM routines WHERE owner_id=? AND visibility!='private' LIMIT 1", (uid,)).fetchone()
            if shared:
                abort(409, 'Este TOP tiene rutinas compartidas. Debe retirar su publicación antes de cambiar a perfil normal.')
        token = None
        if action == 'reset':
            if not target['active']:
                abort(409, 'Reactiva primero la cuenta.')
            token = secrets.token_urlsafe(32)
            db().execute('DELETE FROM invitations WHERE user_id=?', (uid,))
            db().execute('INSERT INTO invitations VALUES (?,?,?)', (digest(token), uid, int(time.time())+86400))
            db().execute('UPDATE users SET password_hash=NULL,revision=revision+1 WHERE id=?', (uid,))
        elif action in ('disable', 'enable'):
            db().execute('UPDATE users SET active=?,revision=revision+1 WHERE id=?', (int(action == 'enable'), uid))
            db().execute('DELETE FROM invitations WHERE user_id=?', (uid,))
        elif action in ('TOP', 'normal'):
            db().execute('UPDATE users SET role=?,revision=revision+1 WHERE id=?', (action, uid))
        else:
            abort(400)
        db().execute('DELETE FROM sessions WHERE user_id=?', (uid,))
        audit('user_' + action, uid)
        db().commit()
        if token:
            return render_template('page.html', page='invitation', token=token, username=target['username'])
        return redirect(url_for('admin'))

    from .catalog import register_catalog
    from .routines import register_routines
    register_catalog(app, db, protected, audit)
    register_routines(app, db, protected, audit)
    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['serve', 'bootstrap', 'migrate'])
    parser.add_argument('--username', default='top')
    parser.add_argument('--area', choices=['training', 'admin'], default='training')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    app = create_app({'AREA': args.area})
    if args.command == 'bootstrap':
        if not re.fullmatch(r'[A-Za-z0-9_.-]{3,64}', args.username):
            raise SystemExit('Nombre de usuario no válido')
        with connect(app.config['DATABASE']) as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                raise SystemExit('El primer TOP ya está creado. Usa la consola para gestionar cuentas.')
            uid, token = str(uuid.uuid4()), secrets.token_urlsafe(32)
            db.execute('INSERT INTO users(id,username,role,created_at) VALUES (?,?,?,?)', (uid, args.username, 'TOP', int(time.time())))
            db.execute('INSERT INTO invitations VALUES (?,?,?)', (digest(token), uid, int(time.time())+86400))
        print('Primer TOP: ' + args.username + '\nCódigo de un solo uso (24 h): ' + token + '\nAbre /activate y establece tu contraseña. No guardes este código en logs.')
    elif args.command == 'serve':
        from waitress import serve
        serve(app, host='127.0.0.1', port=args.port, threads=4)
    else:
        print('Migraciones 001 y 002 aplicadas; datos conservados.')

if __name__ == '__main__':
    main()
