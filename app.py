import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from database.db import (
    get_db, init_db, seed_db, create_user, get_user_by_email,
    get_user_by_id, get_recent_expenses, get_expense_stats, get_category_totals,
)

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

    db_user = get_user_by_id(session["user_id"])
    if not db_user:
        session.clear()
        return redirect(url_for("login"))

    member_since = datetime.strptime(
        db_user["created_at"], "%Y-%m-%d %H:%M:%S"
    ).strftime("%B %d, %Y")

    user = {
        "name":         db_user["name"],
        "email":        db_user["email"],
        "member_since": member_since,
    }

    raw = get_expense_stats(session["user_id"])
    stats = {
        "total_spent":       f"${raw['total_spent']:.2f}",
        "transaction_count": raw["transaction_count"],
        "top_category":      raw["top_category"],
    }

    transactions = [
        {
            "date":        datetime.strptime(tx["date"], "%Y-%m-%d").strftime("%b %d, %Y"),
            "description": tx["description"],
            "category":    tx["category"],
            "amount":      f"${tx['amount']:.2f}",
        }
        for tx in get_recent_expenses(session["user_id"])
    ]

    categories = get_category_totals(session["user_id"])

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
