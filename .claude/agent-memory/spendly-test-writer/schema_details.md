---
name: schema-details
description: Finalised SQLite schema for users and expenses tables as of 2026-06-21
metadata:
  type: project
---

## users table

```sql
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    DEFAULT (datetime('now'))
);
```

- `email` has a UNIQUE constraint — duplicate inserts raise `sqlite3.IntegrityError`
- `created_at` stored as TEXT in SQLite datetime format: `"YYYY-MM-DD HH:MM:SS"`
- Passwords hashed with `werkzeug.security.generate_password_hash`

## expenses table

```sql
CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,   -- stored as "YYYY-MM-DD"
    description TEXT,               -- nullable
    created_at  TEXT    DEFAULT (datetime('now'))
);
```

- Foreign key `user_id → users(id)` enforced via `PRAGMA foreign_keys = ON` in `get_db()`
- `description` is nullable (no NOT NULL constraint)
- `date` stored as `"YYYY-MM-DD"` string; formatted to `"Mon DD, YYYY"` in the profile route
- `amount` is REAL (float); formatted to `"$X.XX"` in the profile route and `get_category_totals`

## Known valid categories in seed data

Food, Transport, Bills, Health, Entertainment, Shopping, Other

**Why:** Schema is finalized and stable — these details should not change
without a migration.  Knowing nullable fields prevents false test failures.
**How to apply:** When writing expense-related tests, description can be None;
always provide amount, category, date, user_id.
