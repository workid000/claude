"""
Tests for public static routes and stub routes in app.py.

Routes covered
--------------
- GET /             (landing page)
- GET /terms        (terms of service)
- GET /privacy      (privacy policy)
- GET /dashboard    (stub)
- GET /expenses/add (stub)
- GET /expenses/<id>/edit   (stub)
- GET /expenses/<id>/delete (stub)

HTTP method enforcement is also tested for routes that should not accept POST.
"""

import pytest


# ===========================================================================
# Landing page  /
# ===========================================================================

class TestLandingRoute:

    def test_landing_get_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_landing_renders_spendly_brand(self, client):
        response = client.get("/")
        assert b"Spendly" in response.data

    def test_landing_is_publicly_accessible_without_session(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_landing_post_returns_405(self, client):
        response = client.post("/")
        assert response.status_code == 405


# ===========================================================================
# Terms of service  /terms
# ===========================================================================

class TestTermsRoute:

    def test_terms_get_returns_200(self, client):
        response = client.get("/terms")
        assert response.status_code == 200

    def test_terms_is_publicly_accessible(self, client):
        response = client.get("/terms")
        assert response.status_code == 200

    def test_terms_post_returns_405(self, client):
        response = client.post("/terms")
        assert response.status_code == 405


# ===========================================================================
# Privacy policy  /privacy
# ===========================================================================

class TestPrivacyRoute:

    def test_privacy_get_returns_200(self, client):
        response = client.get("/privacy")
        assert response.status_code == 200

    def test_privacy_is_publicly_accessible(self, client):
        response = client.get("/privacy")
        assert response.status_code == 200

    def test_privacy_post_returns_405(self, client):
        response = client.post("/privacy")
        assert response.status_code == 405


# ===========================================================================
# Stub routes
# ===========================================================================

class TestDashboardStub:

    def test_dashboard_get_returns_200(self, client):
        response = client.get("/dashboard")
        assert response.status_code == 200


class TestAddExpenseStub:

    def test_add_expense_get_returns_200(self, client):
        response = client.get("/expenses/add")
        assert response.status_code == 200


class TestEditExpenseStub:

    def test_edit_expense_get_returns_200_for_integer_id(self, client):
        response = client.get("/expenses/1/edit")
        assert response.status_code == 200

    def test_edit_expense_with_nonexistent_id_returns_200(self, client):
        """Stub route returns a plain string regardless of id value."""
        response = client.get("/expenses/99999/edit")
        assert response.status_code == 200

    def test_edit_expense_with_non_integer_id_returns_404(self, client):
        """Flask's <int:id> converter rejects non-numeric segments."""
        response = client.get("/expenses/abc/edit")
        assert response.status_code == 404


class TestDeleteExpenseStub:

    def test_delete_expense_get_returns_200_for_integer_id(self, client):
        response = client.get("/expenses/1/delete")
        assert response.status_code == 200

    def test_delete_expense_with_nonexistent_id_returns_200(self, client):
        response = client.get("/expenses/99999/delete")
        assert response.status_code == 200

    def test_delete_expense_with_non_integer_id_returns_404(self, client):
        response = client.get("/expenses/abc/delete")
        assert response.status_code == 404


# ===========================================================================
# 404 behaviour
# ===========================================================================

class TestNotFound:

    def test_unknown_route_returns_404(self, client):
        response = client.get("/this-route-does-not-exist")
        assert response.status_code == 404
