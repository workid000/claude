"""
Shared pytest fixtures for the Spendly test suite.

DB isolation strategy
---------------------
database/db.py uses a module-level DB_PATH constant; every call to get_db()
opens a new sqlite3 connection to that path.  In-memory SQLite (':memory:')
cannot be shared across connections, so we instead patch DB_PATH to a
temporary file path for each test.  The tmp_path fixture provides a
per-test directory that pytest cleans up automatically.

The 'app' and 'client' fixtures use this patched DB_PATH so the Flask
app's own calls to init_db() / seed_db() also hit the temp file.
"""

import sqlite3
import pytest
import database.db as db_module
from app import app as flask_app


# ---------------------------------------------------------------------------
# DB helpers used directly in fixtures
# ---------------------------------------------------------------------------

def _init_schema(db_path: str) -> None:
    """Create tables in the given SQLite file without touching DB_PATH."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_db_path(tmp_path):
    """Return a path to a fresh, schema-initialised SQLite file."""
    path = str(tmp_path / "test_spendly.db")
    _init_schema(path)
    return path


@pytest.fixture(autouse=False)
def patched_db(test_db_path, monkeypatch):
    """
    Patch database.db.DB_PATH so every db helper call in this test uses
    the isolated temp file.  Also patches the name as imported into app.py
    via 'from database.db import get_db …' — those imports bind to the
    function objects, not the constant, so patching DB_PATH on the module
    is sufficient because get_db() reads DB_PATH at call time.
    """
    monkeypatch.setattr(db_module, "DB_PATH", test_db_path)
    return test_db_path


@pytest.fixture
def client(patched_db):
    """
    Flask test client backed by the patched, isolated test database.
    The app is configured for testing and the secret key is kept as-is
    so session behaviour matches production.
    """
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.test_client() as c:
        # init_db is safe to call multiple times (uses IF NOT EXISTS)
        with flask_app.app_context():
            db_module.init_db()
        yield c


@pytest.fixture
def seeded_client(patched_db):
    """
    Flask test client with the demo seed data pre-loaded.
    Useful for profile tests that need the 8 seeded expenses.
    """
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.test_client() as c:
        with flask_app.app_context():
            db_module.init_db()
            db_module.seed_db()
        yield c


@pytest.fixture
def registered_user(patched_db):
    """
    Insert a known test user directly via the DB helper and return their
    credentials dict.  Does NOT use the Flask client so it works for both
    route tests and direct DB tests.
    """
    user_id = db_module.create_user(
        name="Test User",
        email="test@example.com",
        password="password123",
    )
    return {
        "id":       user_id,
        "name":     "Test User",
        "email":    "test@example.com",
        "password": "password123",
    }


@pytest.fixture
def auth_client(client, registered_user):
    """
    Flask test client with a valid session already established for the
    registered_user fixture.  Use this for any test that requires an
    authenticated user.
    """
    client.post(
        "/login",
        data={
            "email":    registered_user["email"],
            "password": registered_user["password"],
        },
        follow_redirects=False,
    )
    return client


@pytest.fixture
def auth_client_with_expenses(auth_client, registered_user, patched_db):
    """
    Authenticated client whose user has a known set of expense rows
    inserted directly into the test DB.
    """
    expenses = [
        (registered_user["id"], 50.00, "Food",      "2026-05-01", "Dinner"),
        (registered_user["id"], 30.00, "Transport",  "2026-05-03", "Taxi"),
        (registered_user["id"], 20.00, "Food",       "2026-05-10", "Lunch"),
        (registered_user["id"], 10.00, "Entertainment", "2026-05-15", "Movie"),
        (registered_user["id"], 40.00, "Bills",      "2026-05-20", "Electricity"),
        (registered_user["id"], 15.00, "Other",      "2026-05-25", "Misc"),
    ]
    conn = sqlite3.connect(patched_db)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()
    return auth_client
