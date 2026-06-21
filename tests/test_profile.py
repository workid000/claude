"""
Tests for the GET /profile route.

Spec reference: Spec 05 — Backend Routes for Profile Page

Coverage
--------
- Unauthenticated access redirects to /login with a flash message
- Deleted-user session edge case clears session and redirects to /login
- Authenticated user sees their own name and email
- member_since is formatted as a human-readable string (e.g. "June 01, 2026")
- stats dict contains total_spent (dollar-formatted), transaction_count, top_category
- transactions list is present and ordered most-recent first
- transaction amounts are dollar-formatted
- transaction dates are formatted as "Mon DD, YYYY"
- categories list contains name, amount (dollar-formatted), pct (integer)
- Profile reflects seeded demo user's 8 expenses when logged in as demo
- Profile does NOT show another user's data
"""

import sqlite3
import pytest
import database.db as db_module
from database.db import create_user, get_user_by_email


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_expense(db_path, user_id, amount, category, date, description=None):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()
    conn.close()


def _login(client, email, password):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


# ===========================================================================
# Unauthenticated access
# ===========================================================================

class TestProfileUnauthenticated:

    def test_unauthenticated_get_redirects_to_login(self, client):
        response = client.get("/profile", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_get_sets_flash_message(self, client):
        response = client.get("/profile", follow_redirects=True)
        assert b"Please log in" in response.data

    def test_unauthenticated_get_does_not_render_profile_template(self, client):
        response = client.get("/profile", follow_redirects=False)
        # A redirect response has no profile-specific content
        assert b"profile-name" not in response.data
        assert b"Member since" not in response.data

    def test_profile_is_not_accessible_via_post(self, client):
        response = client.post("/profile")
        assert response.status_code == 405


# ===========================================================================
# Deleted-user edge case
# ===========================================================================

class TestProfileDeletedUser:

    def test_deleted_user_session_redirects_to_login(self, client, patched_db):
        """
        Inject a session with a user_id that does not exist in the DB.
        The route must clear the session and redirect to /login.
        """
        with client.session_transaction() as sess:
            sess["user_id"]   = 99999
            sess["user_name"] = "Ghost"

        response = client.get("/profile", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_deleted_user_session_is_cleared(self, client, patched_db):
        with client.session_transaction() as sess:
            sess["user_id"]   = 99999
            sess["user_name"] = "Ghost"

        client.get("/profile")
        with client.session_transaction() as sess:
            assert "user_id" not in sess


# ===========================================================================
# Authenticated access — HTTP behaviour
# ===========================================================================

class TestProfileAuthenticated:

    def test_profile_returns_200_for_authenticated_user(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200

    def test_profile_renders_profile_template_content(self, auth_client):
        response = auth_client.get("/profile")
        assert b"Member since" in response.data


# ===========================================================================
# User context variable
# ===========================================================================

class TestProfileUserContext:

    def test_profile_displays_logged_in_user_name(self, auth_client, registered_user):
        response = auth_client.get("/profile")
        assert registered_user["name"].encode() in response.data

    def test_profile_displays_logged_in_user_email(self, auth_client, registered_user):
        response = auth_client.get("/profile")
        assert registered_user["email"].encode() in response.data

    def test_profile_member_since_is_human_readable(self, auth_client):
        """
        The member_since value must be a human-readable string like
        "June 01, 2026", not a raw ISO datetime like "2026-06-01 12:00:00".
        """
        response = auth_client.get("/profile")
        body = response.data.decode()
        # A raw ISO datetime would contain 'T' or seconds like ':00'
        # A formatted date would contain a month name
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        assert any(m in body for m in months), \
            "member_since should contain a full month name"

    def test_profile_does_not_show_raw_iso_datetime_for_member_since(self, auth_client):
        response = auth_client.get("/profile")
        body = response.data.decode()
        # Raw SQLite datetime format contains colons inside a time component
        # e.g. "2026-06-01 14:30:00" — we check that this pattern is absent
        # from the "Member since" context
        import re
        # Find the Member since line and verify no 00:00:00 pattern next to it
        assert not re.search(r"Member since.*\d{4}-\d{2}-\d{2} \d{2}:\d{2}", body)

    def test_profile_does_not_display_other_users_name(self, client, patched_db):
        uid1 = create_user("Alice", "alice@test.com", "pw")
        uid2 = create_user("Bob",   "bob@test.com",   "pw")
        _login(client, "alice@test.com", "pw")
        response = client.get("/profile")
        body = response.data.decode()
        assert "Alice" in body
        assert "Bob" not in body


# ===========================================================================
# Stats context variable
# ===========================================================================

class TestProfileStatsContext:

    def test_profile_stats_total_spent_is_dollar_formatted(self, auth_client_with_expenses):
        response = auth_client_with_expenses.get("/profile")
        body = response.data.decode()
        # Must contain a dollar sign followed by a numeric value
        import re
        assert re.search(r"\$\d+\.\d{2}", body), \
            "total_spent should be formatted as $X.XX"

    def test_profile_stats_total_spent_reflects_actual_sum(
        self, auth_client_with_expenses
    ):
        """
        The fixture inserts: 50 + 30 + 20 + 10 + 40 + 15 = 165.00
        """
        response = auth_client_with_expenses.get("/profile")
        assert b"$165.00" in response.data

    def test_profile_stats_transaction_count_reflects_actual_count(
        self, auth_client_with_expenses
    ):
        """The fixture inserts 6 expense rows."""
        response = auth_client_with_expenses.get("/profile")
        assert b"6" in response.data

    def test_profile_stats_top_category_is_food(self, auth_client_with_expenses):
        """
        Food total = 50 + 20 = 70.  Bills = 40.  Transport = 30.
        Top category must be Food.
        """
        response = auth_client_with_expenses.get("/profile")
        assert b"Food" in response.data

    def test_profile_stats_top_category_is_dash_when_no_expenses(
        self, auth_client
    ):
        response = auth_client.get("/profile")
        assert "—".encode() in response.data

    def test_profile_stats_total_spent_is_zero_when_no_expenses(self, auth_client):
        response = auth_client.get("/profile")
        assert b"$0.00" in response.data


# ===========================================================================
# Transactions context variable
# ===========================================================================

class TestProfileTransactionsContext:

    def test_profile_transactions_are_present_in_response(
        self, auth_client_with_expenses
    ):
        response = auth_client_with_expenses.get("/profile")
        # The template renders a <table> with transaction rows
        assert b"<table" in response.data or b"data-table" in response.data

    def test_profile_transactions_show_category_names(
        self, auth_client_with_expenses
    ):
        response = auth_client_with_expenses.get("/profile")
        body = response.data.decode()
        # At least one of the inserted categories should appear
        assert "Food" in body or "Transport" in body or "Bills" in body

    def test_profile_transactions_amount_is_dollar_formatted(
        self, auth_client_with_expenses
    ):
        response = auth_client_with_expenses.get("/profile")
        import re
        assert re.search(r"\$\d+\.\d{2}", response.data.decode())

    def test_profile_transactions_date_is_human_readable(
        self, auth_client_with_expenses
    ):
        """
        Dates must be formatted as "Mon DD, YYYY" (e.g. "May 01, 2026"),
        not the raw "YYYY-MM-DD" stored in the DB.
        """
        response = auth_client_with_expenses.get("/profile")
        body = response.data.decode()
        months_short = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        assert any(m in body for m in months_short)

    def test_profile_transactions_ordered_most_recent_first(
        self, client, patched_db, registered_user
    ):
        """
        Insert two expenses with different dates; the more recent one
        must appear before the earlier one in the rendered HTML.
        """
        _login(client, registered_user["email"], registered_user["password"])
        _insert_expense(patched_db, registered_user["id"], 10.0, "Food", "2026-01-01", "Older")
        _insert_expense(patched_db, registered_user["id"], 20.0, "Food", "2026-06-15", "Newer")
        response = client.get("/profile")
        body = response.data.decode()
        pos_newer = body.find("Newer")
        pos_older = body.find("Older")
        assert pos_newer < pos_older, \
            "More recent transaction must appear before older one in the page"

    def test_profile_transactions_limited_to_five_by_default(
        self, client, patched_db, registered_user
    ):
        """Insert 8 expenses; only the 5 most recent should appear."""
        _login(client, registered_user["email"], registered_user["password"])
        for i in range(1, 9):
            _insert_expense(
                patched_db,
                registered_user["id"],
                float(i * 10),
                "Other",
                f"2026-01-{i:02d}",
                f"Expense {i}",
            )
        response = client.get("/profile")
        body = response.data.decode()
        # "Expense 1" through "Expense 3" are the earliest; they should NOT appear
        assert "Expense 1" not in body
        assert "Expense 2" not in body
        assert "Expense 3" not in body
        # "Expense 8" is most recent and must appear
        assert "Expense 8" in body

    def test_profile_transactions_description_displayed(
        self, client, patched_db, registered_user
    ):
        _login(client, registered_user["email"], registered_user["password"])
        _insert_expense(
            patched_db, registered_user["id"], 25.0, "Food", "2026-05-10",
            "Special lunch description"
        )
        response = client.get("/profile")
        assert b"Special lunch description" in response.data


# ===========================================================================
# Categories context variable
# ===========================================================================

class TestProfileCategoriesContext:

    def test_profile_categories_section_present(self, auth_client_with_expenses):
        response = auth_client_with_expenses.get("/profile")
        assert b"Spending by Category" in response.data

    def test_profile_categories_shows_category_names(self, auth_client_with_expenses):
        response = auth_client_with_expenses.get("/profile")
        body = response.data.decode()
        assert "Food" in body

    def test_profile_categories_empty_when_no_expenses(self, auth_client):
        """No expenses = empty category list; page must still render without error."""
        response = auth_client.get("/profile")
        assert response.status_code == 200

    def test_profile_categories_pct_values_are_integers_in_template(
        self, auth_client_with_expenses
    ):
        """
        The template uses cat.pct as a CSS width percentage.
        Check that no floating-point artefact like '33.333' appears.
        """
        import re
        response = auth_client_with_expenses.get("/profile")
        body = response.data.decode()
        # category-bar-fill uses style="width: X%" — pct must be whole number
        matches = re.findall(r'width:\s*([\d.]+)%', body)
        for m in matches:
            assert "." not in m, f"pct value '{m}' should be an integer, not a float"


# ===========================================================================
# Demo user (seeded data)
# ===========================================================================

class TestProfileDemoUser:

    def test_demo_user_profile_returns_200(self, seeded_client):
        _login(seeded_client, "demo@spendly.com", "demo123")
        response = seeded_client.get("/profile")
        assert response.status_code == 200

    def test_demo_user_profile_shows_correct_name(self, seeded_client):
        _login(seeded_client, "demo@spendly.com", "demo123")
        response = seeded_client.get("/profile")
        assert b"Demo User" in response.data

    def test_demo_user_profile_shows_correct_email(self, seeded_client):
        _login(seeded_client, "demo@spendly.com", "demo123")
        response = seeded_client.get("/profile")
        assert b"demo@spendly.com" in response.data

    def test_demo_user_stats_transaction_count_is_eight(self, seeded_client):
        _login(seeded_client, "demo@spendly.com", "demo123")
        response = seeded_client.get("/profile")
        # The stats card shows the transaction count
        assert b"8" in response.data

    def test_demo_user_stats_total_spent_is_correct(self, seeded_client):
        """
        Seeded expenses: 12.50 + 45.00 + 120.00 + 35.00 + 25.00 + 68.99 + 15.00 + 22.75
        = 344.24
        """
        _login(seeded_client, "demo@spendly.com", "demo123")
        response = seeded_client.get("/profile")
        assert b"$344.24" in response.data

    def test_demo_user_top_category_is_bills(self, seeded_client):
        """
        Bills total = 120.00 (highest single-category spend).
        """
        _login(seeded_client, "demo@spendly.com", "demo123")
        response = seeded_client.get("/profile")
        assert b"Bills" in response.data

    def test_demo_user_most_recent_transaction_is_groceries(self, seeded_client):
        """
        Most recent seeded expense is 2026-06-15 "Groceries" (Food).
        """
        _login(seeded_client, "demo@spendly.com", "demo123")
        response = seeded_client.get("/profile")
        assert b"Groceries" in response.data

    def test_demo_user_food_category_appears_in_breakdown(self, seeded_client):
        _login(seeded_client, "demo@spendly.com", "demo123")
        response = seeded_client.get("/profile")
        assert b"Food" in response.data
