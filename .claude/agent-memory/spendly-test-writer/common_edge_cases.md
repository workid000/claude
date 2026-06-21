---
name: common-edge-cases
description: Edge cases discovered while writing the Spendly test suite
metadata:
  type: feedback
---

## DB layer edge cases

- `get_expense_stats` on user with no expenses: `total_spent = 0.0`, `transaction_count = 0`, `top_category = "—"` (em-dash U+2014, not hyphen)
- `get_category_totals` with amount=0 rows: grand total is 0 → must return `pct=0` not raise `ZeroDivisionError`
- `seed_db()` skips if `COUNT(*) FROM users > 0` — so calling it after `create_user()` does nothing; the `seeded_client` fixture must call `seed_db()` on a clean DB
- `sqlite3.IntegrityError` on FK violation only fires when `PRAGMA foreign_keys = ON` — `get_db()` sets this, but direct `sqlite3.connect()` calls in tests must also set it

## Registration edge cases

- Whitespace-only name (e.g. "   ") is stripped by `.strip()` and treated as empty → "All fields are required." error
- Duplicate email check happens at the DB layer (IntegrityError), not pre-validation — so the order of checks matters: empty fields and password mismatch are caught before the DB insert

## Login edge cases

- Wrong-case email: SQLite TEXT equality is case-sensitive; `get_user_by_email("IVAN@TEST.COM")` may not match "ivan@test.com" — test documents this without mandating normalisation
- Generic error message: must not hint whether the email exists — avoid "not registered" or "no account" strings

## Profile route edge cases

- Deleted-user session: inject `session["user_id"] = 99999` directly via `session_transaction()` to simulate a user row that was deleted after login; route must call `session.clear()`
- `member_since` formatting: stored as `"YYYY-MM-DD HH:MM:SS"`, must be displayed as `"Month DD, YYYY"` — test checks for full month name presence and absence of raw ISO format
- Transaction ordering: explicitly test that a newer-dated expense appears before an older one in the rendered HTML (position check)
- 5-row transaction limit: insert 8 expenses, verify that the earliest 3 are absent from the page

## HTTP method enforcement

- `/logout` only accepts GET; POST returns 405 (Flask default for methods not in `methods=[]`)
- `/profile` only accepts GET; POST returns 405
- Static pages (/, /terms, /privacy) reject POST with 405
- Stub routes with `<int:id>` reject non-integer path segments with 404 (Flask converter)

**Why:** These cases were non-obvious during spec review and required careful
attention to SQLite behaviour, Flask routing, and template rendering details.
**How to apply:** Re-check these cases when extending tests for new features.
