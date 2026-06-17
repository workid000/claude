# Spec: Login and Logout

## Overview
Implement session-based login and logout so registered users can authenticate into Spendly. This step upgrades the stub `GET /login` route into a full `GET`/`POST` handler that verifies credentials against the `users` table, stores the authenticated user's id and name in Flask's signed session cookie, and redirects to the dashboard (or a placeholder until Step 5). The `GET /logout` stub is replaced with a handler that clears the session and redirects to the landing page. After this step, the app has a complete authentication boundary that all protected routes can gate behind.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (`create_user()`, confirmed password hashing with werkzeug)

## Routes
- `GET /login` — render login form — public (already exists as stub, upgrade it)
- `POST /login` — validate credentials, set session, redirect to `/dashboard` placeholder — public
- `GET /logout` — clear session, redirect to `/` — logged-in (already exists as stub, upgrade it)

## Database changes
No new tables or columns needed.

One new DB helper must be added to `database/db.py`:
- `get_user_by_email(email)` — queries `users` by email using a parameterised query, returns a `sqlite3.Row` (or `None` if not found). The caller is responsible for verifying the password with `werkzeug`.

## Templates
- **Modify**: `templates/login.html`
  - Change the form `action` to `url_for('login')` with `method="post"`
  - Ensure inputs have `name` attributes: `email`, `password`
  - Add a block to display flashed error messages (e.g. "Invalid email or password")
  - Keep all existing visual design
- **Modify**: `templates/base.html`
  - Conditionally show "Log out" link in the navbar when `session.user_id` is set
  - Conditionally show "Log in" / "Register" links when no session exists

## Files to change
- `app.py` — upgrade `login()` to handle `GET` and `POST`; implement `logout()`; add a `/dashboard` placeholder stub
- `database/db.py` — add `get_user_by_email(email)` helper
- `templates/login.html` — wire up form action/method and flash message display
- `templates/base.html` — conditional navbar links based on session state

## Files to create
None.

## New dependencies
No new dependencies. Uses `werkzeug.security.check_password_hash` (already installed) and Flask's built-in `session`, `flash`, `redirect`, `url_for`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings in SQL
- Verify passwords with `werkzeug.security.check_password_hash` — never compare plaintext
- Store only `user_id` (int) and `user_name` (str) in `session` — never store the password hash
- `app.secret_key` is already set in `app.py` — do not change it
- On login failure, use a generic message ("Invalid email or password") — do not reveal whether the email exists
- On successful login, redirect to `url_for('dashboard')` (stub is acceptable for now)
- `logout()` must call `session.clear()` then redirect to `url_for('landing')`
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- Use `url_for()` for every internal link — never hardcode URLs

## Definition of done
- [ ] `GET /login` renders the login form without errors
- [ ] Submitting the form with a valid email and correct password sets the session and redirects to `/dashboard`
- [ ] Submitting with a valid email but wrong password re-renders the form with "Invalid email or password", no session set
- [ ] Submitting with an unregistered email re-renders the form with "Invalid email or password", no session set
- [ ] Submitting with any empty field re-renders the form with a validation error
- [ ] `GET /logout` clears the session and redirects to `/`
- [ ] Visiting `/logout` when not logged in redirects to `/` without error
- [ ] The navbar shows "Log out" when logged in and "Log in" / "Register" when not logged in
- [ ] `session` never contains a password or password hash — verifiable by printing `dict(session)` in a route
