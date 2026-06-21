# Spec: Backend Routes for Profile Page

## Overview
This feature replaces all hardcoded data in the `/profile` route with real database queries. The profile page UI was built in Step 4 with static placeholder data; Step 5 wires that template to the actual `users` and `expenses` tables. The route will look up the logged-in user by their session `user_id`, fetch their recent transactions, and compute summary statistics (total spent, transaction count, top category, per-category breakdown) using raw SQL aggregation queries added to `database/db.py`.

## Depends on
- Step 1: Database setup (`users` and `expenses` tables must exist)
- Step 2: Registration (real user rows must be creatable)
- Step 3: Login + Logout (session `user_id` must be set correctly on sign-in)
- Step 4: Profile page design (`templates/profile.html` must exist with the expected context variables)

## Routes
- `GET /profile` — fetch real user + expense data and render profile page — logged-in only (redirect to `/login` if not authenticated)

No new routes. The existing `/profile` route is updated in place.

## Database changes
No new tables or columns. Four new query functions are added to `database/db.py`:

- `get_user_by_id(user_id)` — `SELECT` a single user row by primary key
- `get_recent_expenses(user_id, limit=5)` — `SELECT` the most recent `limit` expense rows for a user, ordered by `date DESC`
- `get_expense_stats(user_id)` — returns a dict with `total_spent` (SUM of amount), `transaction_count` (COUNT), and `top_category` (category with highest SUM)
- `get_category_totals(user_id)` — returns a list of dicts `{name, amount, pct}` where `pct` is each category's share of the total, ordered by amount DESC; `pct` is 0 when total is 0

## Templates
- **Modify:** `templates/profile.html` — no structural changes; the Jinja expressions already reference `user`, `stats`, `transactions`, and `categories` context variables. Only the data source changes (real DB vs hardcoded). Verify that `user.member_since` is formatted as a human-readable string (e.g. "January 15, 2025") — format in the route, not the template.

## Files to change
- `app.py` — update the `/profile` view function to call the four new DB helpers instead of building hardcoded dicts; format `member_since` from the raw `created_at` ISO string
- `database/db.py` — add `get_user_by_id`, `get_recent_expenses`, `get_expense_stats`, `get_category_totals`

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never string-format SQL values
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- If `get_user_by_id` returns `None` (deleted account edge case), call `session.clear()` and redirect to `/login`
- `member_since` must be formatted with Python's `datetime.strptime` / `strftime` — do not import a new library
- `pct` values in `get_category_totals` must be integers (use integer division or `round()`)
- Each DB helper must open its own connection and close it before returning

## Definition of done
- [ ] Visiting `/profile` while logged in shows the real logged-in user's name and email (not "Alex Johnson")
- [ ] The `member_since` field displays a human-readable date matching the account's `created_at` value
- [ ] The total spent stat reflects the actual sum of that user's expenses
- [ ] The transaction count stat equals the actual number of expense rows for that user
- [ ] The top category stat names the category with the highest total spend for that user
- [ ] The transaction history table lists real expense rows (date, description, category, amount) ordered most-recent first
- [ ] The category breakdown lists real per-category totals with correct percentages that sum to ~100 %
- [ ] Logging in as the seeded `demo@spendly.com` account shows the 8 seeded expenses
- [ ] Visiting `/profile` without a session still redirects to `/login`
- [ ] No hardcoded placeholder data remains in the `/profile` route in `app.py`
