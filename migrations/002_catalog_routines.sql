CREATE TABLE machines (
 id TEXT PRIMARY KEY, creator_id TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL,
 sticker TEXT, zone TEXT NOT NULL DEFAULT '', brand TEXT NOT NULL DEFAULT '', model TEXT NOT NULL DEFAULT '',
 description TEXT NOT NULL DEFAULT '', instructions TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL CHECK(status IN ('provisional','approved','archived')),
 canonical_id TEXT REFERENCES machines(id), revision INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL,
 CHECK(canonical_id IS NULL OR canonical_id != id)
);
CREATE UNIQUE INDEX machine_active_sticker ON machines(sticker COLLATE NOCASE) WHERE sticker IS NOT NULL AND status != 'archived';
CREATE TABLE machine_requests (
 id TEXT PRIMARY KEY, machine_id TEXT NOT NULL UNIQUE REFERENCES machines(id), creator_id TEXT NOT NULL REFERENCES users(id),
 state TEXT NOT NULL CHECK(state IN ('pending','info','approved','linked','rejected')), message TEXT NOT NULL DEFAULT '', revision INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE request_resolutions (
 id TEXT PRIMARY KEY, request_id TEXT NOT NULL REFERENCES machine_requests(id), actor_id TEXT NOT NULL REFERENCES users(id),
 action TEXT NOT NULL, message TEXT NOT NULL DEFAULT '', target_id TEXT REFERENCES machines(id), created_at INTEGER NOT NULL
);
CREATE TABLE private_notes (
 owner_id TEXT NOT NULL REFERENCES users(id), machine_id TEXT NOT NULL REFERENCES machines(id),
 body TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(owner_id,machine_id)
);
CREATE TABLE exercises (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', muscles TEXT NOT NULL DEFAULT '',
 equipment TEXT NOT NULL CHECK(equipment IN ('machine','cable','barbell','dumbbell','bodyweight','other')),
 archived INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE exercise_machines (
 exercise_id TEXT NOT NULL REFERENCES exercises(id), machine_id TEXT NOT NULL REFERENCES machines(id), PRIMARY KEY(exercise_id,machine_id)
);
CREATE TABLE routines (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id), visibility TEXT NOT NULL DEFAULT 'private' CHECK(visibility IN ('private','public','assigned')),
 archived INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1, current_number INTEGER NOT NULL DEFAULT 1,
 copied_from TEXT REFERENCES routines(id), created_at INTEGER NOT NULL
);
CREATE TABLE routine_versions (
 id TEXT PRIMARY KEY, routine_id TEXT NOT NULL REFERENCES routines(id), number INTEGER NOT NULL,
 name TEXT NOT NULL, date_from TEXT NOT NULL, date_until TEXT, created_at INTEGER NOT NULL, UNIQUE(routine_id,number),
 CHECK(date_until IS NULL OR date_until>=date_from)
);
CREATE TABLE routine_days (
 version_id TEXT NOT NULL REFERENCES routine_versions(id), weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
 title TEXT NOT NULL DEFAULT '', rest INTEGER NOT NULL CHECK(rest IN (0,1)), PRIMARY KEY(version_id,weekday)
);
CREATE TABLE routine_items (
 version_id TEXT NOT NULL, weekday INTEGER NOT NULL, item_key TEXT NOT NULL, position INTEGER NOT NULL,
 exercise_id TEXT NOT NULL REFERENCES exercises(id), machine_id TEXT REFERENCES machines(id), original_machine_id TEXT REFERENCES machines(id),
 exercise_name TEXT NOT NULL, machine_name TEXT NOT NULL DEFAULT '', sticker TEXT, reps_json TEXT NOT NULL, rest_seconds INTEGER NOT NULL CHECK(rest_seconds BETWEEN 0 AND 3600),
 PRIMARY KEY(version_id,item_key), FOREIGN KEY(version_id,weekday) REFERENCES routine_days(version_id,weekday)
);
CREATE TABLE routine_assignments (
 routine_id TEXT NOT NULL REFERENCES routines(id), user_id TEXT NOT NULL REFERENCES users(id), PRIMARY KEY(routine_id,user_id)
);
CREATE TABLE planning (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id), routine_id TEXT NOT NULL REFERENCES routines(id),
 date_from TEXT NOT NULL, date_until TEXT, revision INTEGER NOT NULL DEFAULT 1, CHECK(date_until IS NULL OR date_until>=date_from)
);
CREATE INDEX planning_owner_dates ON planning(owner_id,date_from,date_until);
INSERT INTO schema_migrations VALUES (2,unixepoch());
