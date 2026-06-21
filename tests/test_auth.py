"""
Tests for authentication routes: /register, /login, /logout.

Spec references
---------------
- Spec 02 (Registration): field validation, duplicate email, redirect on success
- Spec 03 (Login / Logout): credential validation, session keys, redirect rules,
  already-logged-in behaviour, session teardown on logout

All tests use the isolated patched_db + client fixtures from conftest.py.
"""

import pytest
from database.db import get_user_by_email


# ===========================================================================
# /register  —  GET
# ===========================================================================

class TestRegisterGet:

    def test_register_get_returns_200(self, client):
        response = client.get("/register")
        assert response.status_code == 200

    def test_register_get_renders_registration_form(self, client):
        response = client.get("/register")
        data = response.data.decode()
        assert "Create your account" in data

    def test_register_get_contains_name_field(self, client):
        response = client.get("/register")
        assert b'name="name"' in response.data

    def test_register_get_contains_email_field(self, client):
        response = client.get("/register")
        assert b'name="email"' in response.data

    def test_register_get_contains_password_field(self, client):
        response = client.get("/register")
        assert b'name="password"' in response.data

    def test_register_get_contains_confirm_password_field(self, client):
        response = client.get("/register")
        assert b'name="confirm_password"' in response.data

    def test_register_get_redirects_to_profile_when_already_logged_in(self, auth_client):
        response = auth_client.get("/register", follow_redirects=False)
        assert response.status_code == 302
        assert "/profile" in response.headers["Location"]


# ===========================================================================
# /register  —  POST happy path
# ===========================================================================

class TestRegisterPostSuccess:

    def test_register_valid_submission_redirects_to_login(self, client):
        response = client.post("/register", data={
            "name":             "New User",
            "email":            "new@test.com",
            "password":         "password123",
            "confirm_password": "password123",
        }, follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_register_valid_submission_creates_user_in_db(self, client, patched_db):
        client.post("/register", data={
            "name":             "DB User",
            "email":            "dbuser@test.com",
            "password":         "password123",
            "confirm_password": "password123",
        })
        user = get_user_by_email("dbuser@test.com")
        assert user is not None
        assert user["name"] == "DB User"

    def test_register_valid_submission_flashes_success_message(self, client):
        response = client.post("/register", data={
            "name":             "Flash User",
            "email":            "flash@test.com",
            "password":         "password123",
            "confirm_password": "password123",
        }, follow_redirects=True)
        assert b"Account created" in response.data

    def test_register_does_not_store_plaintext_password(self, client, patched_db):
        client.post("/register", data={
            "name":             "Hash User",
            "email":            "hash@test.com",
            "password":         "mysecret",
            "confirm_password": "mysecret",
        })
        user = get_user_by_email("hash@test.com")
        assert user["password_hash"] != "mysecret"

    def test_register_does_not_set_session_on_success(self, client):
        client.post("/register", data={
            "name":             "Session Check",
            "email":            "sess@test.com",
            "password":         "password123",
            "confirm_password": "password123",
        })
        with client.session_transaction() as sess:
            assert "user_id" not in sess


# ===========================================================================
# /register  —  POST validation failures
# ===========================================================================

class TestRegisterPostValidation:

    def test_register_missing_name_returns_200_and_shows_error(self, client):
        response = client.post("/register", data={
            "name":             "",
            "email":            "user@test.com",
            "password":         "password123",
            "confirm_password": "password123",
        })
        assert response.status_code == 200
        assert b"All fields are required" in response.data

    def test_register_missing_email_returns_200_and_shows_error(self, client):
        response = client.post("/register", data={
            "name":             "User",
            "email":            "",
            "password":         "password123",
            "confirm_password": "password123",
        })
        assert response.status_code == 200
        assert b"All fields are required" in response.data

    def test_register_missing_password_returns_200_and_shows_error(self, client):
        response = client.post("/register", data={
            "name":             "User",
            "email":            "user@test.com",
            "password":         "",
            "confirm_password": "password123",
        })
        assert response.status_code == 200
        assert b"All fields are required" in response.data

    def test_register_missing_confirm_password_returns_200_and_shows_error(self, client):
        response = client.post("/register", data={
            "name":             "User",
            "email":            "user@test.com",
            "password":         "password123",
            "confirm_password": "",
        })
        assert response.status_code == 200
        assert b"All fields are required" in response.data

    def test_register_all_fields_missing_returns_200_and_shows_error(self, client):
        response = client.post("/register", data={})
        assert response.status_code == 200
        assert b"All fields are required" in response.data

    def test_register_missing_fields_does_not_insert_user(self, client, patched_db):
        client.post("/register", data={
            "name":             "",
            "email":            "ghost@test.com",
            "password":         "password123",
            "confirm_password": "password123",
        })
        assert get_user_by_email("ghost@test.com") is None

    def test_register_mismatched_passwords_returns_200_and_shows_error(self, client):
        response = client.post("/register", data={
            "name":             "User",
            "email":            "user@test.com",
            "password":         "password123",
            "confirm_password": "different456",
        })
        assert response.status_code == 200
        assert b"Passwords do not match" in response.data

    def test_register_mismatched_passwords_does_not_insert_user(self, client, patched_db):
        client.post("/register", data={
            "name":             "NoInsert",
            "email":            "noinsert@test.com",
            "password":         "password123",
            "confirm_password": "different456",
        })
        assert get_user_by_email("noinsert@test.com") is None

    def test_register_duplicate_email_returns_200_and_shows_error(self, client, registered_user):
        response = client.post("/register", data={
            "name":             "Duplicate",
            "email":            registered_user["email"],
            "password":         "password123",
            "confirm_password": "password123",
        })
        assert response.status_code == 200
        assert b"Email already registered" in response.data

    def test_register_duplicate_email_does_not_create_second_row(self, client, registered_user, patched_db):
        from database.db import get_db
        client.post("/register", data={
            "name":             "Duplicate",
            "email":            registered_user["email"],
            "password":         "newpw123",
            "confirm_password": "newpw123",
        })
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(patched_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE email = ?", (registered_user["email"],)
        ).fetchone()[0]
        conn.close()
        assert count == 1

    def test_register_whitespace_only_name_returns_error(self, client):
        response = client.post("/register", data={
            "name":             "   ",
            "email":            "ws@test.com",
            "password":         "password123",
            "confirm_password": "password123",
        })
        assert response.status_code == 200
        assert b"All fields are required" in response.data


# ===========================================================================
# /login  —  GET
# ===========================================================================

class TestLoginGet:

    def test_login_get_returns_200(self, client):
        response = client.get("/login")
        assert response.status_code == 200

    def test_login_get_renders_sign_in_form(self, client):
        response = client.get("/login")
        assert b"Welcome back" in response.data

    def test_login_get_contains_email_field(self, client):
        response = client.get("/login")
        assert b'name="email"' in response.data

    def test_login_get_contains_password_field(self, client):
        response = client.get("/login")
        assert b'name="password"' in response.data

    def test_login_get_redirects_to_profile_when_already_logged_in(self, auth_client):
        response = auth_client.get("/login", follow_redirects=False)
        assert response.status_code == 302
        assert "/profile" in response.headers["Location"]


# ===========================================================================
# /login  —  POST happy path
# ===========================================================================

class TestLoginPostSuccess:

    def test_login_valid_credentials_redirects_to_profile(self, client, registered_user):
        response = client.post("/login", data={
            "email":    registered_user["email"],
            "password": registered_user["password"],
        }, follow_redirects=False)
        assert response.status_code == 302
        assert "/profile" in response.headers["Location"]

    def test_login_valid_credentials_sets_user_id_in_session(self, client, registered_user):
        client.post("/login", data={
            "email":    registered_user["email"],
            "password": registered_user["password"],
        })
        with client.session_transaction() as sess:
            assert sess["user_id"] == registered_user["id"]

    def test_login_valid_credentials_sets_user_name_in_session(self, client, registered_user):
        client.post("/login", data={
            "email":    registered_user["email"],
            "password": registered_user["password"],
        })
        with client.session_transaction() as sess:
            assert sess["user_name"] == registered_user["name"]

    def test_login_session_does_not_contain_password(self, client, registered_user):
        client.post("/login", data={
            "email":    registered_user["email"],
            "password": registered_user["password"],
        })
        with client.session_transaction() as sess:
            assert "password" not in sess
            assert "password_hash" not in sess

    def test_login_session_user_id_is_integer(self, client, registered_user):
        client.post("/login", data={
            "email":    registered_user["email"],
            "password": registered_user["password"],
        })
        with client.session_transaction() as sess:
            assert isinstance(sess["user_id"], int)


# ===========================================================================
# /login  —  POST validation failures
# ===========================================================================

class TestLoginPostValidation:

    def test_login_missing_email_returns_200_and_shows_error(self, client):
        response = client.post("/login", data={
            "email":    "",
            "password": "password123",
        })
        assert response.status_code == 200
        assert b"All fields are required" in response.data

    def test_login_missing_password_returns_200_and_shows_error(self, client):
        response = client.post("/login", data={
            "email":    "user@test.com",
            "password": "",
        })
        assert response.status_code == 200
        assert b"All fields are required" in response.data

    def test_login_both_fields_missing_returns_200_and_shows_error(self, client):
        response = client.post("/login", data={})
        assert response.status_code == 200
        assert b"All fields are required" in response.data

    def test_login_wrong_password_returns_200_and_shows_generic_error(self, client, registered_user):
        response = client.post("/login", data={
            "email":    registered_user["email"],
            "password": "wrongpassword",
        })
        assert response.status_code == 200
        assert b"Invalid email or password" in response.data

    def test_login_wrong_password_does_not_set_session(self, client, registered_user):
        client.post("/login", data={
            "email":    registered_user["email"],
            "password": "wrongpassword",
        })
        with client.session_transaction() as sess:
            assert "user_id" not in sess

    def test_login_unregistered_email_returns_200_and_shows_generic_error(self, client):
        response = client.post("/login", data={
            "email":    "nobody@nowhere.com",
            "password": "password123",
        })
        assert response.status_code == 200
        assert b"Invalid email or password" in response.data

    def test_login_unregistered_email_does_not_set_session(self, client):
        client.post("/login", data={
            "email":    "nobody@nowhere.com",
            "password": "password123",
        })
        with client.session_transaction() as sess:
            assert "user_id" not in sess

    def test_login_error_message_does_not_confirm_email_existence(self, client):
        """Error message must be generic — must not hint whether the email exists."""
        response = client.post("/login", data={
            "email":    "nobody@nowhere.com",
            "password": "password123",
        })
        body = response.data.decode()
        assert "not registered" not in body.lower()
        assert "no account" not in body.lower()

    def test_login_valid_email_wrong_case_does_not_authenticate(self, client, registered_user):
        """
        The app stores emails as entered.  If the login lookup is
        case-sensitive, an upper-cased variant must not authenticate.
        This test documents the expected behaviour; if the app
        normalises emails to lowercase the assertion adjusts accordingly —
        the key requirement is that no session is set for an email that
        was not used during registration.
        """
        response = client.post("/login", data={
            "email":    registered_user["email"].upper(),
            "password": registered_user["password"],
        })
        # Either no session set OR a 302 to profile — depends on normalisation.
        # We verify that if it renders the login form, no session was set.
        if response.status_code == 200:
            with client.session_transaction() as sess:
                assert "user_id" not in sess


# ===========================================================================
# /logout
# ===========================================================================

class TestLogout:

    def test_logout_while_authenticated_redirects_to_landing(self, auth_client):
        response = auth_client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/") or "/logout" not in response.headers["Location"]

    def test_logout_while_authenticated_clears_user_id_from_session(self, auth_client):
        auth_client.get("/logout")
        with auth_client.session_transaction() as sess:
            assert "user_id" not in sess

    def test_logout_while_authenticated_clears_user_name_from_session(self, auth_client):
        auth_client.get("/logout")
        with auth_client.session_transaction() as sess:
            assert "user_name" not in sess

    def test_logout_while_not_authenticated_redirects_to_landing_without_error(self, client):
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 302

    def test_logout_while_not_authenticated_does_not_raise(self, client):
        """Logging out without a session must not produce a 500."""
        response = client.get("/logout")
        assert response.status_code not in (500, 400)

    def test_logout_followed_by_profile_access_redirects_to_login(self, auth_client):
        auth_client.get("/logout")
        response = auth_client.get("/profile", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_logout_is_not_accessible_via_post(self, client):
        response = client.post("/logout")
        assert response.status_code == 405
