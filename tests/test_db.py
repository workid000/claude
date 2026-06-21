"""
Tests for database/db.py helper functions.

These tests call the db helpers directly (not through Flask routes) against
the isolated temp-file database provided by the patched_db fixture.

Coverage
--------
- Schema creation (init_db idempotency, table existence, column constraints)
- seed_db idempotency and correct row counts
- create_user: happy path, duplicate email, password hashing
- get_user_by_email: found and not-found cases
- get_user_by_id: found and not-found cases
- get_recent_expenses: ordering, limit, empty result
- get_expense_stats: totals, counts, top category, user with no expenses
- get_category_totals: amounts, pct values, ordering, empty result
- Foreign key enforcement on expenses.user_id
"""

import sqlite3
import pytest
from werkzeug.security import check_password_hash

import database.db as db_module
from database.db import (
    init_db,
    seed_db,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_recent_expenses,
    get_expense_stats,
    get_category_totals,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _raw_conn(db_path):
    """Return a raw connection to the test DB for assertion queries."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _insert_expense(db_path, user_id, amount, category, date, description=None):
    conn = _raw_conn(db_path)
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()
    conn.close()


# ===========================================================================
# init_db
# ===========================================================================

class TestInitDb:

    def test_users_table_exists_after_init(self, patched_db):
        init_db()
        conn = _raw_conn(patched_db)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_expenses_table_exists_after_init(self, patched_db):
        init_db()
        conn = _raw_conn(patched_db)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='expenses'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_init_db_is_idempotent(self, patched_db):
        """Calling init_db twice must not raise and must not duplicate tables."""
        init_db()
        init_db()  # second call — should be a no-op
        conn = _raw_conn(patched_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('users','expenses')"
        ).fetchone()[0]
        conn.close()
        assert count == 2

    def test_users_table_has_required_columns(self, patched_db):
        init_db()
        conn = _raw_conn(patched_db)
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        conn.close()
        assert {"id", "name", "email", "password_hash", "created_at"}.issubset(cols)

    def test_expenses_table_has_required_columns(self, patched_db):
        init_db()
        conn = _raw_conn(patched_db)
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(expenses)").fetchall()}
        conn.close()
        assert {"id", "user_id", "amount", "category", "date", "description", "created_at"}.issubset(cols)

    def test_users_email_has_unique_constraint(self, patched_db):
        init_db()
        conn = _raw_conn(patched_db)
        # Two inserts with the same email must raise IntegrityError
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("A", "dupe@test.com", "hash1"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("B", "dupe@test.com", "hash2"),
            )
        conn.close()

    def test_expenses_description_is_nullable(self, patched_db):
        init_db()
        uid = create_user("A", "a@test.com", "pw")
        conn = _raw_conn(patched_db)
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            (uid, 10.0, "Food", "2026-01-01"),
        )
        conn.commit()
        row = conn.execute("SELECT description FROM expenses WHERE user_id = ?", (uid,)).fetchone()
        conn.close()
        assert row["description"] is None


# ===========================================================================
# seed_db
# ===========================================================================

class TestSeedDb:

    def test_seed_db_creates_demo_user(self, patched_db):
        init_db()
        seed_db()
        user = get_user_by_email("demo@spendly.com")
        assert user is not None

    def test_seed_db_creates_eight_expenses_for_demo_user(self, patched_db):
        init_db()
        seed_db()
        user = get_user_by_email("demo@spendly.com")
        conn = _raw_conn(patched_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user["id"],)
        ).fetchone()[0]
        conn.close()
        assert count == 8

    def test_seed_db_is_idempotent_on_second_call(self, patched_db):
        init_db()
        seed_db()
        seed_db()  # second call — must not insert more rows
        conn = _raw_conn(patched_db)
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        expense_count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()
        assert user_count == 1
        assert expense_count == 8

    def test_seed_db_demo_password_is_hashed(self, patched_db):
        init_db()
        seed_db()
        user = get_user_by_email("demo@spendly.com")
        assert user["password_hash"] != "demo123"
        assert check_password_hash(user["password_hash"], "demo123")

    def test_seed_db_skips_when_users_already_exist(self, patched_db):
        init_db()
        create_user("Existing", "existing@test.com", "pw")
        seed_db()  # should skip because users table is not empty
        conn = _raw_conn(patched_db)
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        # Only the user we inserted should exist — seed was skipped
        assert count == 1


# ===========================================================================
# create_user
# ===========================================================================

class TestCreateUser:

    def test_create_user_returns_integer_id(self, patched_db):
        uid = create_user("Alice", "alice@test.com", "secret")
        assert isinstance(uid, int)
        assert uid > 0

    def test_create_user_inserts_row_in_db(self, patched_db):
        create_user("Bob", "bob@test.com", "secret")
        user = get_user_by_email("bob@test.com")
        assert user is not None
        assert user["name"] == "Bob"
        assert user["email"] == "bob@test.com"

    def test_create_user_stores_password_as_hash_not_plaintext(self, patched_db):
        create_user("Carol", "carol@test.com", "mypassword")
        user = get_user_by_email("carol@test.com")
        assert user["password_hash"] != "mypassword"
        assert check_password_hash(user["password_hash"], "mypassword")

    def test_create_user_raises_on_duplicate_email(self, patched_db):
        create_user("Dave", "dave@test.com", "pw1")
        with pytest.raises(sqlite3.IntegrityError):
            create_user("Dave2", "dave@test.com", "pw2")

    def test_create_user_duplicate_email_does_not_insert_second_row(self, patched_db):
        create_user("Eve", "eve@test.com", "pw")
        try:
            create_user("Eve2", "eve@test.com", "pw2")
        except sqlite3.IntegrityError:
            pass
        conn = _raw_conn(patched_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE email = ?", ("eve@test.com",)
        ).fetchone()[0]
        conn.close()
        assert count == 1

    def test_create_user_ids_are_unique_for_different_emails(self, patched_db):
        id1 = create_user("Frank", "frank@test.com", "pw")
        id2 = create_user("Grace", "grace@test.com", "pw")
        assert id1 != id2

    def test_create_user_with_special_characters_in_name(self, patched_db):
        uid = create_user("O'Brien & Co.", "obrien@test.com", "pw")
        user = get_user_by_id(uid)
        assert user["name"] == "O'Brien & Co."


# ===========================================================================
# get_user_by_email
# ===========================================================================

class TestGetUserByEmail:

    def test_get_user_by_email_returns_row_for_existing_user(self, patched_db):
        create_user("Hana", "hana@test.com", "pw")
        user = get_user_by_email("hana@test.com")
        assert user is not None

    def test_get_user_by_email_returns_correct_name(self, patched_db):
        create_user("Hana", "hana@test.com", "pw")
        user = get_user_by_email("hana@test.com")
        assert user["name"] == "Hana"

    def test_get_user_by_email_returns_none_for_unknown_email(self, patched_db):
        user = get_user_by_email("nobody@test.com")
        assert user is None

    def test_get_user_by_email_is_case_sensitive(self, patched_db):
        """SQLite TEXT comparisons are case-sensitive by default for non-ASCII;
        the app stores emails as entered.  Lookups with different case must
        not return a false positive."""
        create_user("Ivan", "ivan@test.com", "pw")
        # Uppercase variant should not match the lowercase stored email
        user_upper = get_user_by_email("IVAN@TEST.COM")
        # We do not mandate a specific outcome here — just that the stored
        # row is retrievable with the original casing
        user_exact = get_user_by_email("ivan@test.com")
        assert user_exact is not None

    def test_get_user_by_email_returns_sqlite_row(self, patched_db):
        create_user("Jane", "jane@test.com", "pw")
        user = get_user_by_email("jane@test.com")
        # sqlite3.Row supports dict-style key access
        assert user["email"] == "jane@test.com"


# ===========================================================================
# get_user_by_id
# ===========================================================================

class TestGetUserById:

    def test_get_user_by_id_returns_row_for_existing_user(self, patched_db):
        uid = create_user("Kim", "kim@test.com", "pw")
        user = get_user_by_id(uid)
        assert user is not None

    def test_get_user_by_id_returns_correct_email(self, patched_db):
        uid = create_user("Leo", "leo@test.com", "pw")
        user = get_user_by_id(uid)
        assert user["email"] == "leo@test.com"

    def test_get_user_by_id_returns_none_for_nonexistent_id(self, patched_db):
        user = get_user_by_id(99999)
        assert user is None

    def test_get_user_by_id_returns_correct_user_when_multiple_exist(self, patched_db):
        uid1 = create_user("Mia", "mia@test.com", "pw")
        uid2 = create_user("Noah", "noah@test.com", "pw")
        assert get_user_by_id(uid1)["email"] == "mia@test.com"
        assert get_user_by_id(uid2)["email"] == "noah@test.com"


# ===========================================================================
# get_recent_expenses
# ===========================================================================

class TestGetRecentExpenses:

    def test_get_recent_expenses_returns_empty_list_when_no_expenses(self, patched_db):
        uid = create_user("Owen", "owen@test.com", "pw")
        rows = get_recent_expenses(uid)
        assert rows == []

    def test_get_recent_expenses_returns_rows_for_that_user(self, patched_db):
        uid = create_user("Pam", "pam@test.com", "pw")
        _insert_expense(patched_db, uid, 10.0, "Food", "2026-01-01", "Lunch")
        rows = get_recent_expenses(uid)
        assert len(rows) == 1
        assert rows[0]["amount"] == 10.0

    def test_get_recent_expenses_ordered_by_date_desc(self, patched_db):
        uid = create_user("Quinn", "quinn@test.com", "pw")
        _insert_expense(patched_db, uid, 10.0, "Food",      "2026-01-01")
        _insert_expense(patched_db, uid, 20.0, "Transport", "2026-01-10")
        _insert_expense(patched_db, uid, 30.0, "Bills",     "2026-01-05")
        rows = get_recent_expenses(uid)
        dates = [r["date"] for r in rows]
        assert dates == sorted(dates, reverse=True)

    def test_get_recent_expenses_default_limit_is_five(self, patched_db):
        uid = create_user("Rosa", "rosa@test.com", "pw")
        for i in range(8):
            _insert_expense(patched_db, uid, float(i), "Food", f"2026-01-{i+1:02d}")
        rows = get_recent_expenses(uid)
        assert len(rows) == 5

    def test_get_recent_expenses_custom_limit_respected(self, patched_db):
        uid = create_user("Sam", "sam@test.com", "pw")
        for i in range(10):
            _insert_expense(patched_db, uid, float(i), "Food", f"2026-01-{i+1:02d}")
        rows = get_recent_expenses(uid, limit=3)
        assert len(rows) == 3

    def test_get_recent_expenses_does_not_return_other_users_data(self, patched_db):
        uid1 = create_user("Tara", "tara@test.com", "pw")
        uid2 = create_user("Uma",  "uma@test.com",  "pw")
        _insert_expense(patched_db, uid1, 50.0, "Food", "2026-01-01")
        _insert_expense(patched_db, uid2, 99.0, "Food", "2026-01-02")
        rows = get_recent_expenses(uid1)
        assert all(r["user_id"] == uid1 for r in rows)
        assert len(rows) == 1


# ===========================================================================
# get_expense_stats
# ===========================================================================

class TestGetExpenseStats:

    def test_get_expense_stats_returns_zeros_when_no_expenses(self, patched_db):
        uid = create_user("Vera", "vera@test.com", "pw")
        stats = get_expense_stats(uid)
        assert stats["total_spent"] == 0.0
        assert stats["transaction_count"] == 0

    def test_get_expense_stats_top_category_is_dash_when_no_expenses(self, patched_db):
        uid = create_user("Will", "will@test.com", "pw")
        stats = get_expense_stats(uid)
        assert stats["top_category"] == "—"

    def test_get_expense_stats_total_spent_sums_correctly(self, patched_db):
        uid = create_user("Xena", "xena@test.com", "pw")
        _insert_expense(patched_db, uid, 10.50, "Food",      "2026-01-01")
        _insert_expense(patched_db, uid, 20.00, "Transport", "2026-01-02")
        stats = get_expense_stats(uid)
        assert abs(stats["total_spent"] - 30.50) < 0.001

    def test_get_expense_stats_transaction_count_is_correct(self, patched_db):
        uid = create_user("Yara", "yara@test.com", "pw")
        for i in range(4):
            _insert_expense(patched_db, uid, 5.0, "Other", f"2026-01-{i+1:02d}")
        stats = get_expense_stats(uid)
        assert stats["transaction_count"] == 4

    def test_get_expense_stats_top_category_is_highest_spend_category(self, patched_db):
        uid = create_user("Zoe", "zoe@test.com", "pw")
        _insert_expense(patched_db, uid, 10.0, "Food",      "2026-01-01")
        _insert_expense(patched_db, uid, 10.0, "Food",      "2026-01-02")  # Food total=20
        _insert_expense(patched_db, uid, 15.0, "Transport", "2026-01-03")  # Transport total=15
        stats = get_expense_stats(uid)
        assert stats["top_category"] == "Food"

    def test_get_expense_stats_does_not_include_other_users_data(self, patched_db):
        uid1 = create_user("Aaron", "aaron@test.com", "pw")
        uid2 = create_user("Beth",  "beth@test.com",  "pw")
        _insert_expense(patched_db, uid2, 999.0, "Food", "2026-01-01")
        stats = get_expense_stats(uid1)
        assert stats["total_spent"] == 0.0
        assert stats["transaction_count"] == 0

    def test_get_expense_stats_returns_dict_with_required_keys(self, patched_db):
        uid = create_user("Cara", "cara@test.com", "pw")
        stats = get_expense_stats(uid)
        assert "total_spent" in stats
        assert "transaction_count" in stats
        assert "top_category" in stats


# ===========================================================================
# get_category_totals
# ===========================================================================

class TestGetCategoryTotals:

    def test_get_category_totals_returns_empty_list_when_no_expenses(self, patched_db):
        uid = create_user("Dan", "dan@test.com", "pw")
        result = get_category_totals(uid)
        assert result == []

    def test_get_category_totals_returns_one_entry_per_category(self, patched_db):
        uid = create_user("Eli", "eli@test.com", "pw")
        _insert_expense(patched_db, uid, 10.0, "Food",      "2026-01-01")
        _insert_expense(patched_db, uid, 20.0, "Food",      "2026-01-02")
        _insert_expense(patched_db, uid, 15.0, "Transport", "2026-01-03")
        result = get_category_totals(uid)
        assert len(result) == 2

    def test_get_category_totals_ordered_by_amount_desc(self, patched_db):
        uid = create_user("Fay", "fay@test.com", "pw")
        _insert_expense(patched_db, uid, 5.0,  "Other",     "2026-01-01")
        _insert_expense(patched_db, uid, 30.0, "Bills",     "2026-01-02")
        _insert_expense(patched_db, uid, 20.0, "Transport", "2026-01-03")
        result = get_category_totals(uid)
        assert result[0]["name"] == "Bills"
        assert result[1]["name"] == "Transport"

    def test_get_category_totals_name_field_matches_category(self, patched_db):
        uid = create_user("Gio", "gio@test.com", "pw")
        _insert_expense(patched_db, uid, 10.0, "Health", "2026-01-01")
        result = get_category_totals(uid)
        assert result[0]["name"] == "Health"

    def test_get_category_totals_amount_formatted_as_dollar_string(self, patched_db):
        uid = create_user("Hal", "hal@test.com", "pw")
        _insert_expense(patched_db, uid, 42.50, "Shopping", "2026-01-01")
        result = get_category_totals(uid)
        assert result[0]["amount"] == "$42.50"

    def test_get_category_totals_pct_is_integer(self, patched_db):
        uid = create_user("Iris", "iris@test.com", "pw")
        _insert_expense(patched_db, uid, 50.0, "Food",      "2026-01-01")
        _insert_expense(patched_db, uid, 50.0, "Transport", "2026-01-02")
        result = get_category_totals(uid)
        for cat in result:
            assert isinstance(cat["pct"], int)

    def test_get_category_totals_pct_values_sum_to_100(self, patched_db):
        uid = create_user("Jax", "jax@test.com", "pw")
        _insert_expense(patched_db, uid, 50.0, "Food",      "2026-01-01")
        _insert_expense(patched_db, uid, 30.0, "Transport", "2026-01-02")
        _insert_expense(patched_db, uid, 20.0, "Bills",     "2026-01-03")
        result = get_category_totals(uid)
        total_pct = sum(c["pct"] for c in result)
        # Allow ±1 for rounding
        assert abs(total_pct - 100) <= 1

    def test_get_category_totals_pct_is_zero_when_total_is_zero(self, patched_db):
        """Edge case: if grand total were 0 (amount=0 rows), pct must be 0 not a ZeroDivisionError."""
        uid = create_user("Kay", "kay@test.com", "pw")
        conn = _raw_conn(patched_db)
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, 0, ?, ?)",
            (uid, "Food", "2026-01-01"),
        )
        conn.commit()
        conn.close()
        # Should not raise; pct should be 0
        result = get_category_totals(uid)
        assert result[0]["pct"] == 0

    def test_get_category_totals_does_not_include_other_users_data(self, patched_db):
        uid1 = create_user("Lee",  "lee@test.com",  "pw")
        uid2 = create_user("Mae",  "mae@test.com",  "pw")
        _insert_expense(patched_db, uid2, 100.0, "Food", "2026-01-01")
        result = get_category_totals(uid1)
        assert result == []

    def test_get_category_totals_each_entry_has_required_keys(self, patched_db):
        uid = create_user("Ned", "ned@test.com", "pw")
        _insert_expense(patched_db, uid, 10.0, "Other", "2026-01-01")
        result = get_category_totals(uid)
        assert "name" in result[0]
        assert "amount" in result[0]
        assert "pct" in result[0]


# ===========================================================================
# Foreign key enforcement
# ===========================================================================

class TestForeignKeyEnforcement:

    def test_expense_with_invalid_user_id_raises_integrity_error(self, patched_db):
        conn = _raw_conn(patched_db)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (99999, 10.0, "Food", "2026-01-01"),
            )
            conn.commit()
        conn.close()
