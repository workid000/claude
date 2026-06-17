import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("register.html")

    name             = request.form.get("name", "").strip()
    email            = request.form.get("email", "").strip()
    password         = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        flash("All fields are required.")
        return render_template("register.html")

    if password != confirm_password:
        flash("Passwords do not match.")
        return render_template("register.html")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        flash("Email already registered.")
        return render_template("register.html")

    flash("Account created! Please sign in.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("login.html")

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        flash("All fields are required.")
        return render_template("login.html")

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password.")
        return render_template("login.html")

    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/dashboard")
def dashboard():
    return "Dashboard — coming in Step 5"


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        flash("Please log in to view your profile.")
        return redirect(url_for("login"))

    user = {
        "name": "Alex Johnson",
        "email": "alex@example.com",
        "member_since": "January 15, 2025",
    }

    stats = {
        "total_spent": "$344.24",
        "transaction_count": 8,
        "top_category": "Bills",
    }

    transactions = [
        {"date": "Jun 15, 2026", "description": "Groceries",      "category": "Food",          "amount": "$22.75"},
        {"date": "Jun 14, 2026", "description": "Miscellaneous",  "category": "Other",         "amount": "$15.00"},
        {"date": "Jun 12, 2026", "description": "Clothes",        "category": "Shopping",      "amount": "$68.99"},
        {"date": "Jun 10, 2026", "description": "Cinema tickets", "category": "Entertainment", "amount": "$25.00"},
        {"date": "Jun 07, 2026", "description": "Pharmacy",       "category": "Health",        "amount": "$35.00"},
    ]

    categories = [
        {"name": "Bills",         "amount": "$120.00", "pct": 35},
        {"name": "Shopping",      "amount": "$68.99",  "pct": 20},
        {"name": "Transport",     "amount": "$45.00",  "pct": 13},
        {"name": "Food",          "amount": "$35.25",  "pct": 10},
        {"name": "Health",        "amount": "$35.00",  "pct": 10},
        {"name": "Entertainment", "amount": "$25.00",  "pct": 7},
        {"name": "Other",         "amount": "$15.00",  "pct": 4},
    ]

    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
