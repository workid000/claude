---
name: protected-routes
description: Routes requiring authentication, redirect behaviour, and session key contract
metadata:
  type: project
---

## Protected routes (login required)

| Route | Method | Behaviour when unauthenticated |
|-------|--------|-------------------------------|
| /profile | GET | flash "Please log in to view your profile." → redirect /login |

## Public routes (no auth required)

- GET / (landing)
- GET /terms
- GET /privacy
- GET /register (redirects to /profile if already logged in)
- GET /login (redirects to /profile if already logged in)
- GET /logout (works even without session — just clears and redirects to /)

## Stub routes (not yet auth-gated in current implementation)

- GET /dashboard
- GET /expenses/add
- GET /expenses/<int:id>/edit
- GET /expenses/<int:id>/delete

These are currently string-returning stubs and do NOT redirect unauthenticated
users.  Auth tests should be added when the stubs are implemented.

## Session keys contract

After successful login:
- `session["user_id"]` — integer PK from users table
- `session["user_name"]` — string display name

After logout:
- All session keys cleared (`session.clear()`)

After registration:
- No session keys set (user must log in separately)

**Why:** Knowing which routes are protected prevents missed auth tests.
**How to apply:** Any new route that serves user data must be tested for
unauthenticated redirect before marking the feature done.
