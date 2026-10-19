"""Session login helpers and CSRF protection."""
from __future__ import annotations

import functools
import hmac
import secrets
from urllib.parse import urlparse

from flask import abort, flash, g, redirect, request, session, url_for

from . import db


def csrf_token() -> str:
    tok = session.get("_csrf")
    if not tok:
        tok = session["_csrf"] = secrets.token_urlsafe(32)
    return tok


# Pure computation endpoints: they change no state and read no account data.
CSRF_EXEMPT = {"api_analyse", "api_scenario"}


def check_csrf():
    """Rejects state-changing requests without a matching token (form field or header)."""
    if request.method in ("GET", "HEAD", "OPTIONS") or request.endpoint in CSRF_EXEMPT:
        return
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
    expected = session.get("_csrf") or ""
    if not expected or not hmac.compare_digest(sent, expected):
        abort(400, description="Your session expired. Reload the page and try again.")


def safe_next(target: str | None, default: str) -> str:
    """Only allow same-site relative redirects (blocks //evil.com and absolute URLs)."""
    if not target:
        return default
    p = urlparse(target)
    if p.scheme or p.netloc or not target.startswith("/") or target.startswith("//"):
        return default
    return target


def load_user():
    g.user = None
    uid = session.get("uid")
    if uid is None or not db.accounts_enabled():
        return
    try:
        g.user = db.get_db().one("SELECT id, email, name, organisation, created_at FROM users WHERE id = ?", (uid,))
    except Exception:  # database unreachable: behave as logged out rather than 500 on every page
        g.user = None
    if g.user is None:
        session.pop("uid", None)


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not db.accounts_enabled():
            flash("Accounts aren't available on this deployment yet.", "warning")
            return redirect(url_for("home"))
        if g.get("user") is None:
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


def init_app(app):
    app.before_request(load_user)
    app.before_request(check_csrf)
    app.jinja_env.globals["csrf_token"] = csrf_token
