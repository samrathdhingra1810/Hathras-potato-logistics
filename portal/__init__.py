"""ColdFlow: cold storage planning for every harvest (Flask app factory)."""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import date, timedelta

from flask import Flask, jsonify, render_template, request

from . import db, security, views_api, views_auth, views_pages
from .core import dataset as ds
from .core.analytics import forecast_seasons, season_status, summary
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


def _estimates() -> list[str]:
    """Hathras modelled seasons whose harvest is already over (labelled as estimates)."""
    return [s for s in forecast_seasons(ds.PRODUCTION_SERIES) if season_status(s)["status"] == "estimate"]


def _forecast_word() -> str:
    """Plural noun for the modelled Hathras seasons: 'estimates', 'forecasts' or both."""
    n_est, n = len(_estimates()), len(forecast_seasons(ds.PRODUCTION_SERIES))
    return "estimates" if n_est == n else "forecasts" if n_est == 0 else "estimates and forecasts"


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

    app.config["STATIC_VERSION"] = static_version(app.static_folder)

    @app.url_defaults
    def version_static_urls(endpoint, values):
        # Content-hashed ?v= so browsers and the service worker fetch new assets after each deploy.
        if endpoint == "static" and "v" not in values:
            values["v"] = app.config["STATIC_VERSION"]

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
            "forecast_seasons": forecast_seasons(ds.PRODUCTION_SERIES),
            "harvested_forecasts": _estimates(),
            "forecast_word": _forecast_word(),
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


def static_version(folder: str) -> str:
    """Short hash of every static file's contents; changes whenever any asset changes."""
    h = hashlib.sha256()
    for root, _dirs, files in sorted(os.walk(folder)):
        for name in sorted(files):
            path = os.path.join(root, name)
            h.update(os.path.relpath(path, folder).encode())
            with open(path, "rb") as f:
                h.update(f.read())
    return h.hexdigest()[:10]


app = create_app()
