---
name: fixture-patterns
description: DB patching strategy and fixture hierarchy for the Spendly pytest suite
metadata:
  type: feedback
---

## DB isolation strategy

`database/db.py` stores a module-level `DB_PATH` constant.  Every `get_db()`
call opens a new `sqlite3.connect(DB_PATH)` — there is no shared connection.
`:memory:` databases cannot be shared across connections, so tests use a
**temporary file** (from pytest's `tmp_path` fixture) and patch `DB_PATH` on
the module object via `monkeypatch.setattr(db_module, "DB_PATH", test_db_path)`.

Because `app.py` imports the db helpers as function objects
(`from database.db import create_user, …`), patching `DB_PATH` on the module
is sufficient — the imported functions all call `get_db()` at runtime and
`get_db()` reads `DB_PATH` from the module namespace at call time.

## Fixture hierarchy

```
test_db_path (tmp_path)
    └── patched_db (monkeypatches DB_PATH)
            ├── client              — bare Flask test client, init_db() only
            ├── seeded_client       — client with seed_db() pre-run (demo data)
            ├── registered_user     — inserts test@example.com / password123 via create_user
            │       └── auth_client — client with that user already logged in
            │               └── auth_client_with_expenses — 6 expenses inserted directly
            └── (direct db tests use patched_db alone)
```

## Key implementation notes

- `patched_db` fixture has `autouse=False` — it must be explicitly requested
- `client` and `seeded_client` both request `patched_db` so they are isolated
- `registered_user` uses `db_module.create_user()` directly — no HTTP round-trip
- `auth_client` logs in via `POST /login`; do not manually set session keys
  (that would bypass the real auth code path)
- Raw SQL for fixture setup uses `sqlite3.connect(patched_db)` directly

**Why:** SQLite :memory: databases are connection-scoped; a temp file is the
simplest way to share state across the multiple connections that the app opens
per request.

**How to apply:** Always use the `patched_db` fixture (directly or transitively)
in any test that touches the DB or the Flask routes.
