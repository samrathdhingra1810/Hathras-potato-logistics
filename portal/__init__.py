"""ColdFlow: cold storage planning for every harvest (Flask app factory)."""
from __future__ import annotations

import os
import secrets
from datetime import date, timedelta

from flask import Flask, jsonify, render_template, request

from . import db, security, views_api, views_auth, views_pages
from .core import dataset as ds
from .core.analytics import summary
from .formatting import FILTERS

TOOLS = [
    {"slug": "production", "endpoint": "tool_production", "name": "Production analytics",
     "blurb": "Area, harvest and yield across six seasons, with YoY change and growth rates."},
    {"slug": "forecast", "endpoint": "tool_forecast", "name": "Harvest forecast",
     "blurb": "Linear-trend projection for the next two seasons with a 95% prediction interval."},
    {"slug": "planner", "endpoint": "tool_planner", "name": "Capacity planner",
     "blurb": "Model cold storage demand against capacity month by month and flag peak-harvest deficits."},
    {"slug": "map", "endpoint": "tool_map", "name": "Block strain map",
     "blurb": "See which development blocks are short of storage at harvest peak."},
]


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    on_vercel = bool(os.environ.get("VERCEL"))
    secret = os.environ.get("SECRET_KEY")
    app.config.update(
        SECRET_KEY=secret or secrets.token_hex(32),
        # Without a fixed key, sessions don't survive across serverless instances, so
        # accounts stay off on Vercel until SECRET_KEY is set. Locally a random key is fine.
        SECRET_KEY_CONFIGURED=bool(secret) or not on_vercel,
        ON_VERCEL=on_vercel,
        DATABASE_URL=os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or "",
        SQLITE_PATH=os.path.join(app.instance_path, "coldflow.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=on_vercel,
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        MAX_CONTENT_LENGTH=512 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    app.jinja_env.filters.update(FILTERS)
    app.json.sort_keys = False

    db.init_app(app)
    security.init_app(app)
    views_pages.init_app(app)
    views_api.init_app(app)
    views_auth.init_app(app)

    @app.context_processor
    def site_context():
        return {
            "site_name": "ColdFlow",
            "district": ds.DISTRICT,
            "source": ds.DATA_SOURCE,
            "tools": TOOLS,
            "headline": summary(ds.PRODUCTION_SERIES),
            "year": date.today().year,
            "accounts_enabled": db.accounts_enabled(),
        }

    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith("/api/"):
            return jsonify(error=e.description), 400
        return render_template("error.html", code=400, title="Something went wrong", message=e.description), 400

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, title="Page not found",
                               message="That page doesn't exist. Try the tools or head back home."), 404

    @app.errorhandler(413)
    def too_large(_e):
        return jsonify(error="That upload is too large (limit 512 KB)."), 413

    @app.after_request
    def headers(resp):
        if request.path.startswith("/static/"):
            resp.headers.setdefault("Cache-Control", "public, max-age=86400")
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        return resp

    return app


app = create_app()
