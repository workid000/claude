---
name: feature-specs
description: Validated spec details for all implemented Spendly modules as of 2026-06-21
metadata:
  type: project
---

## Module 1 — Database (Spec 01)

- `get_db()` returns `sqlite3.Row`-factory connection with `PRAGMA foreign_keys = ON`
- `init_db()` uses `CREATE TABLE IF NOT EXISTS` — safe to call multiple times
- `seed_db()` skips if `COUNT(*) FROM users > 0` (not idempotent on non-empty DB)
- `create_user(name, email, password)` hashes password with werkzeug, returns new `int` id
- `get_recent_expenses(user_id, limit=5)` — default limit is 5, ordered `date DESC`
- `get_expense_stats(user_id)` — returns dict `{total_spent: float, transaction_count: int, top_category: str}`; top_category is `"—"` (em-dash) when no expenses
- `get_category_totals(user_id)` — returns list of `{name: str, amount: "$X.XX", pct: int}`; ordered by amount DESC; empty list when no expenses; pct is 0 when grand total is 0

## Module 2 — Registration (Spec 02)

- POST /register validation order: (1) empty fields → "All fields are required.", (2) password mismatch → "Passwords do not match.", (3) duplicate email → "Email already registered."
- On success: flash "Account created! Please sign in." then redirect to /login
- Already-logged-in user hitting GET /register → redirect to /profile
- No session is set after registration (user must log in separately)

## Module 3 — Login / Logout (Spec 03)

- POST /login validation order: (1) empty fields → "All fields are required.", (2) bad credentials → "Invalid email or password."
- Session keys set on login: `session["user_id"]` (int), `session["user_name"]` (str)
- Session must NOT contain "password" or "password_hash"
- GET /logout — `session.clear()` then redirect to `/` (landing) — works even without a session
- Already-logged-in user hitting GET /login → redirect to /profile
- /logout only accepts GET; POST returns 405

## Module 4 — Profile Route (Spec 05)

- Route: `GET /profile` — login-required
- Unauthenticated → flash "Please log in to view your profile." + redirect to /login
- If `get_user_by_id(session["user_id"])` returns None → `session.clear()` + redirect to /login
- `member_since` formatted with `datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%B %d, %Y")`
- `stats["total_spent"]` formatted as `f"${raw:.2f}"`
- `transactions` list: each `{date: "Mon DD, YYYY", description, category, amount: "$X.XX"}`; limited to 5
- `categories` list: from `get_category_totals()` — already formatted with dollar amounts and integer pcts
- Profile does NOT accept POST (405)

## Seeded demo data (for profile tests)

- Email: demo@spendly.com, Password: demo123, Name: Demo User
- 8 expenses, amounts: 12.50, 45.00, 120.00, 35.00, 25.00, 68.99, 15.00, 22.75
- Total: $344.24
- Top category: Bills (120.00)
- Most recent: "2026-06-15" — Groceries (Food)
- 5 most recent (for transactions list): 2026-06-15, 2026-06-14, 2026-06-12, 2026-06-10, 2026-06-07

**Why:** Seeded data is deterministic and used for profile integration tests.
**How to apply:** Use `seeded_client` fixture when testing demo-user scenarios.
