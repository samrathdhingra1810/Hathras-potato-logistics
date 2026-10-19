"""Hathras Potato Logistics: a regional information portal (Flask)."""
from __future__ import annotations

import csv
import io
from datetime import date

from flask import Flask, Response, abort, jsonify, render_template, request

from .core import dataset as ds
from .core.analytics import forecast_series, summary, with_yoy
from .core.storage import block_strain, facility_coverage, simulate_storage_year, storage_demand
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


def _num_arg(source, key, default, lo, hi):
    """Reads a bounded number from query/JSON; falls back to default when missing or out of range."""
    try:
        v = float(source.get(key, default))
    except (TypeError, ValueError):
        return default
    return v if lo <= v <= hi else default


def _scenario(source) -> dict:
    """Planner inputs -> demand, simulation and block strain for one season."""
    series = with_yoy(ds.PRODUCTION_SERIES)
    fc = forecast_series(ds.PRODUCTION_SERIES, 2)
    seasons = {series[-1]["season"]: series[-1]["production_t"]}
    seasons.update({r["season"]: r["production_t"] for r in fc["rows"]})

    season = source.get("season") or series[-1]["season"]
    if season not in seasons:
        season = series[-1]["season"]
    ratio = _num_arg(source, "ratio", ds.DEFAULT_STORAGE_RATIO, 0.05, 1)
    capacity = _num_arg(source, "capacity", ds.DEFAULT_REGIONAL_CAPACITY_T, 1, 1e8)
    threshold = _num_arg(source, "threshold", ds.DEFAULT_ALERT_THRESHOLD, 0.5, 1)
    facility = _num_arg(source, "facility", 10_000, 1, 1e7)

    production = seasons[season]
    demand = storage_demand(production, ratio)
    sim = simulate_storage_year(demand_t=demand, capacity_t=capacity, alert_threshold=threshold,
                                intake_profile=ds.MONTHLY_INTAKE_PROFILE, release_profile=ds.MONTHLY_RELEASE_PROFILE)
    return {
        "inputs": {"season": season, "ratio": ratio, "capacity": capacity, "threshold": threshold, "facility": facility},
        "seasons": [{"value": s, "label": f"{s} {'actual' if s == series[-1]['season'] else 'forecast'}"} for s in seasons],
        "production_t": production,
        "demand_t": demand,
        "facility_coverage": facility_coverage(facility, demand),
        "district_coverage": capacity / demand if demand else None,
        "facilities_to_close_gap": max(demand - capacity, 0) / facility,
        "simulation": sim,
        "blocks": block_strain(ds.BLOCKS, demand_t=demand, capacity_t=capacity, alert_threshold=threshold),
    }


def create_app() -> Flask:
    app = Flask(__name__)
    app.jinja_env.filters.update(FILTERS)
    app.json.sort_keys = False

    @app.context_processor
    def site_context():
        return {
            "site_name": "Hathras Potato Logistics",
            "district": ds.DISTRICT,
            "source": ds.DATA_SOURCE,
            "tools": TOOLS,
            "headline": summary(ds.PRODUCTION_SERIES),
            "year": date.today().year,
        }

    # ---------- Pages ----------
    @app.get("/")
    def home():
        scenario = _scenario({})
        return render_template("home.html", series=with_yoy(ds.PRODUCTION_SERIES), scenario=scenario,
                               forecast=forecast_series(ds.PRODUCTION_SERIES, 2))

    @app.get("/about")
    def about():
        return render_template("about.html", assumptions=ds.ASSUMPTIONS)

    @app.get("/services")
    def services():
        return render_template("services.html")

    @app.get("/tools")
    def tools():
        return render_template("tools/index.html", scenario=_scenario({}),
                               forecast=forecast_series(ds.PRODUCTION_SERIES, 2))

    @app.get("/tools/production")
    def tool_production():
        return render_template("tools/production.html", series=with_yoy(ds.PRODUCTION_SERIES))

    @app.get("/tools/forecast")
    def tool_forecast():
        return render_template("tools/forecast.html", series=with_yoy(ds.PRODUCTION_SERIES),
                               forecast=forecast_series(ds.PRODUCTION_SERIES, 2))

    @app.get("/tools/planner")
    def tool_planner():
        return render_template("tools/planner.html", scenario=_scenario(request.args))

    @app.get("/tools/map")
    def tool_map():
        return render_template("tools/map.html", scenario=_scenario(request.args))

    @app.get("/data")
    def data():
        return render_template("data.html", series=with_yoy(ds.PRODUCTION_SERIES), assumptions=ds.ASSUMPTIONS,
                               blocks=ds.BLOCKS)

    @app.get("/data/production.csv")
    def production_csv():
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["season", "area_ha", "production_t", "yield_kg_ha"])
        for r in ds.PRODUCTION_SERIES:
            w.writerow([r["season"], r["area_ha"], r["production_t"], r["yield_kg_ha"]])
        return Response(buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=hathras-potato-production.csv"})

    # ---------- JSON API ----------
    @app.get("/api/health")
    def api_health():
        return jsonify(ok=True)

    @app.get("/api/baseline")
    def api_baseline():
        return jsonify(district=ds.DISTRICT, source=ds.DATA_SOURCE, series=with_yoy(ds.PRODUCTION_SERIES),
                       blocks=ds.BLOCKS, assumptions=ds.ASSUMPTIONS)

    @app.get("/api/forecast")
    def api_forecast():
        horizon = int(_num_arg(request.args, "horizon", 2, 1, 5))
        return jsonify(forecast_series(ds.PRODUCTION_SERIES, horizon))

    @app.route("/api/scenario", methods=["GET", "POST"])
    def api_scenario():
        source = (request.get_json(silent=True) or {}) if request.method == "POST" else request.args
        return jsonify(_scenario(source))

    @app.route("/api/<path:_rest>")
    def api_not_found(_rest):
        return jsonify(error="Not found"), 404

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    @app.after_request
    def cache_headers(resp):
        if request.path.startswith("/static/"):
            resp.headers.setdefault("Cache-Control", "public, max-age=86400")
        return resp

    return app


app = create_app()
