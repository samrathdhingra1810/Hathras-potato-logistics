"""Accounts: sign up, log in/out, dashboard, account settings, plan deletion."""
from __future__ import annotations

import re

from flask import abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash as _gen_hash

from . import db
from .security import login_required, safe_next

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8
# PBKDF2 works on every Python build (macOS system Python lacks hashlib.scrypt).
PASSWORD_METHOD = "pbkdf2:sha256:600000"


def generate_password_hash(password: str) -> str:
    return _gen_hash(password, method=PASSWORD_METHOD)

# Compared against when the email is unknown, so both paths cost one hash check.
_DUMMY_HASH = generate_password_hash("not-a-real-password-placeholder")


def _accounts_or_notice():
    if not db.accounts_enabled():
        return render_template("auth/unavailable.html"), 503
    return None


def _start_session(user_id: int, remember: bool):
    session.clear()  # new session id on login (prevents fixation)
    session["uid"] = user_id
    session.permanent = remember


def init_app(app):
    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if (resp := _accounts_or_notice()):
            return resp
        if g.user:
            return redirect(url_for("dashboard"))
        form = {"name": "", "email": "", "organisation": ""}
        errors = {}
        if request.method == "POST":
            form = {k: (request.form.get(k) or "").strip() for k in form}
            form["email"] = form["email"].lower()
            password = request.form.get("password") or ""
            confirm = request.form.get("confirm") or ""
            if not form["name"]:
                errors["name"] = "Enter your name."
            elif len(form["name"]) > 80:
                errors["name"] = "Keep your name under 80 characters."
            if not EMAIL_RE.match(form["email"]) or len(form["email"]) > 254:
                errors["email"] = "Enter a valid email address."
            if len(form["organisation"]) > 120:
                errors["organisation"] = "Keep this under 120 characters."
            if len(password) < MIN_PASSWORD:
                errors["password"] = f"Use at least {MIN_PASSWORD} characters."
            elif password != confirm:
                errors["confirm"] = "Passwords don't match."
            if not request.form.get("terms"):
                errors["terms"] = "Please accept the terms to continue."
            conn = db.get_db()
            if not errors and conn.one("SELECT id FROM users WHERE email = ?", (form["email"],)):
                errors["email"] = "An account with this email already exists. Log in instead."
            if not errors:
                uid = conn.insert(
                    "INSERT INTO users (email, name, organisation, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                    (form["email"], form["name"], form["organisation"], generate_password_hash(password), db.now()))
                conn.commit()
                _start_session(uid, remember=True)
                flash(f"Welcome to ColdFlow, {form['name'].split()[0]}.", "success")
                return redirect(safe_next(request.args.get("next"), url_for("dashboard")))
        return render_template("auth/signup.html", form=form, errors=errors), (422 if errors else 200)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if (resp := _accounts_or_notice()):
            return resp
        nxt = safe_next(request.args.get("next"), url_for("dashboard"))
        if g.user:
            return redirect(nxt)
        email, error = "", None
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            row = db.get_db().one("SELECT id, password_hash FROM users WHERE email = ?", (email,))
            ok = check_password_hash(row["password_hash"] if row else _DUMMY_HASH, password)
            if row and ok:
                _start_session(row["id"], remember=bool(request.form.get("remember")))
                return redirect(nxt)
            error = "That email and password don't match an account."
        return render_template("auth/login.html", email=email, error=error, next=nxt), (401 if error else 200)

    @app.post("/logout")
    def logout():
        session.clear()
        flash("You've been logged out.", "info")
        return redirect(url_for("home"))

    @app.get("/dashboard")
    @login_required
    def dashboard():
        plans = db.get_db().all(
            "SELECT id, name, created_at, updated_at FROM plans WHERE user_id = ? ORDER BY updated_at DESC", (g.user["id"],))
        return render_template("dashboard.html", plans=plans)

    @app.post("/plans/<int:plan_id>/delete")
    @login_required
    def plan_delete(plan_id):
        conn = db.get_db()
        cur = conn.execute("DELETE FROM plans WHERE id = ? AND user_id = ?", (plan_id, g.user["id"]))
        conn.commit()
        if cur.rowcount == 0:
            abort(404)
        flash("Plan deleted.", "info")
        return redirect(url_for("dashboard"))

    @app.route("/account", methods=["GET", "POST"])
    @login_required
    def account():
        conn = db.get_db()
        errors = {}
        action = request.form.get("action") if request.method == "POST" else None

        if action == "profile":
            name = (request.form.get("name") or "").strip()
            org = (request.form.get("organisation") or "").strip()
            if not name or len(name) > 80:
                errors["name"] = "Enter a name under 80 characters."
            if len(org) > 120:
                errors["organisation"] = "Keep this under 120 characters."
            if not errors:
                conn.execute("UPDATE users SET name = ?, organisation = ? WHERE id = ?", (name, org, g.user["id"]))
                conn.commit()
                flash("Profile updated.", "success")
                return redirect(url_for("account"))

        elif action == "password":
            row = conn.one("SELECT password_hash FROM users WHERE id = ?", (g.user["id"],))
            new = request.form.get("new_password") or ""
            if not check_password_hash(row["password_hash"], request.form.get("current_password") or ""):
                errors["current_password"] = "Your current password is incorrect."
            elif len(new) < MIN_PASSWORD:
                errors["new_password"] = f"Use at least {MIN_PASSWORD} characters."
            elif new != (request.form.get("confirm") or ""):
                errors["confirm"] = "Passwords don't match."
            if not errors:
                conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new), g.user["id"]))
                conn.commit()
                flash("Password changed.", "success")
                return redirect(url_for("account"))

        elif action == "delete":
            row = conn.one("SELECT password_hash FROM users WHERE id = ?", (g.user["id"],))
            if not check_password_hash(row["password_hash"], request.form.get("delete_password") or ""):
                errors["delete_password"] = "Enter your password to delete your account."
            else:
                conn.execute("DELETE FROM plans WHERE user_id = ?", (g.user["id"],))
                conn.execute("DELETE FROM users WHERE id = ?", (g.user["id"],))
                conn.commit()
                session.clear()
                flash("Your account and saved plans have been deleted.", "info")
                return redirect(url_for("home"))

        return render_template("account.html", errors=errors, action=action), (422 if errors else 200)
