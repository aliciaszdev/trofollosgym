PRAGMA foreign_keys=ON;
CREATE TABLE users (
 id TEXT PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE UNIQUE,
 role TEXT NOT NULL CHECK(role IN ('TOP','normal')), active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 password_hash TEXT, created_at INTEGER NOT NULL, height_cm REAL CHECK(height_cm > 0), revision INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, expires_at INTEGER NOT NULL);
CREATE TABLE invitations (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at INTEGER NOT NULL);
CREATE TABLE login_attempts (scope TEXT PRIMARY KEY, failures INTEGER NOT NULL, reset_at INTEGER NOT NULL);
CREATE TABLE audit (id TEXT PRIMARY KEY, actor_id TEXT REFERENCES users(id), action TEXT NOT NULL, target_id TEXT, created_at INTEGER NOT NULL);
CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL);
INSERT INTO schema_migrations VALUES (1,unixepoch());
