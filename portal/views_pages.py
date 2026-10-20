"""Public pages: landing, Hathras regional pages, own-data planner, info pages."""
from __future__ import annotations

import csv
import io
import json

from flask import Response, abort, current_app, g, jsonify, render_template, request, send_from_directory

from . import db
from .core import dataset as ds
from .core.analytics import compare_models, forecast_series, with_yoy
from .core.custom import hathras_example
from .core.geo import distance_matrix
from .core import districts
from .roles import ROLES, workspace_data
from .scenario import hathras_scenario


def init_app(app):
    @app.get("/")
    def home():
        scenario = hathras_scenario({})
        forecast = forecast_series(ds.PRODUCTION_SERIES, 2)
        return render_template("landing.html", scenario=scenario, forecast=forecast,
                               chips=home_chips(scenario, forecast))

    @app.get("/hathras")
    def hathras():
        return render_template("hathras.html", series=with_yoy(ds.PRODUCTION_SERIES), scenario=hathras_scenario({}),
                               forecast=forecast_series(ds.PRODUCTION_SERIES, 2))

    @app.get("/tools")
    def tools():
        return render_template("tools/index.html", scenario=hathras_scenario({}),
                               forecast=forecast_series(ds.PRODUCTION_SERIES, 2))

    @app.get("/tools/production")
    def tool_production():
        return render_template("tools/production.html", series=with_yoy(ds.PRODUCTION_SERIES))

    @app.get("/tools/forecast")
    def tool_forecast():
        return render_template("tools/forecast.html", series=with_yoy(ds.PRODUCTION_SERIES),
                               forecast=forecast_series(ds.PRODUCTION_SERIES, 2),
                               compare=compare_models(ds.PRODUCTION_SERIES, 2))

    @app.get("/tools/planner")
    def tool_planner():
        return render_template("tools/planner.html", scenario=hathras_scenario(request.args))

    @app.get("/tools/map")
    def tool_map():
        return render_template("tools/map.html", scenario=hathras_scenario(request.args),
                               distances=distance_matrix(ds.BLOCKS))

    @app.get("/plan")
    def plan():
        """Own-data planner. ?plan=<id> opens one of the signed-in user's saved plans."""
        saved = None
        plan_id = request.args.get("plan", type=int)
        if plan_id and g.get("user"):
            row = db.get_db().one("SELECT id, name, payload, updated_at FROM plans WHERE id = ? AND user_id = ?",
                                  (plan_id, g.user["id"]))
            if row:
                saved = {"id": row["id"], "name": row["name"], "updated_at": row["updated_at"],
                         "payload": json.loads(row["payload"])}
        return render_template("plan.html", example=hathras_example(), saved=saved,
                               accounts=db.accounts_enabled(), districts=districts.listing())

    @app.get("/workspace")
    @app.get("/workspace/<role>")
    def workspace(role=None):
        if role is None:
            role = (g.user or {}).get("role") or "owner"
        if role not in ROLES:
            abort(404)
        return render_template("workspace.html", ws=workspace_data(role), roles=ROLES)

    @app.get("/api/districts")
    def api_districts():
        return jsonify(districts.listing())

    @app.get("/api/districts/<district_id>")
    def api_district(district_id):
        p = districts.payload_for(district_id)
        if p is None:
            return jsonify(error="No verified dataset is loaded for that district yet."), 404
        return jsonify(p)

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

    @app.get("/about")
    def about():
        return render_template("about.html", assumptions=ds.ASSUMPTIONS)

    @app.get("/services")
    def services():
        return render_template("services.html")

    @app.get("/manifest.webmanifest")
    def manifest():
        return send_from_directory(current_app.static_folder, "manifest.webmanifest",
                                   mimetype="application/manifest+json")

    @app.get("/sw.js")
    def service_worker():
        # Served from the root so it can control every page.
        v = current_app.config["STATIC_VERSION"]
        resp = Response(render_template("sw.js", version=v), mimetype="application/javascript")
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["Service-Worker-Allowed"] = "/"
        return resp

    @app.get("/offline")
    def offline():
        return render_template("offline.html")

    @app.get("/privacy")
    def privacy():
        return render_template("legal/privacy.html")

    @app.get("/terms")
    def terms():
        return render_template("legal/terms.html")


def _kt(t: float) -> str:
    return f"{abs(t) / 1000:.1f}k T" if abs(t) < 1e5 else f"{abs(t) / 1000:.0f}k T"


def home_chips(scenario: dict, forecast: dict) -> list[dict]:
    """Floating hero chips, computed from the live Hathras scenario (never hard-coded figures)."""
    blocks = {b["id"]: b for b in scenario["blocks"]}

    def gap(bid):
        b = blocks[bid]
        sign = "+" if b["gap_t"] >= 0 else "−"
        return {"icon": "📍", "text": f"{b['name']} ({sign}{_kt(b['gap_t'])})", "tone": "good" if b["gap_t"] >= 0 else "bad"}

    def full(bid):
        b = blocks[bid]
        return {"icon": "📍", "text": f"{b['name']} ({b['utilisation'] * 100:.1f}% full)",
                "tone": "bad" if b["utilisation"] > 1 else "warn" if b["utilisation"] >= 0.75 else "good"}

    sim = scenario["simulation"]
    peak_intake = max(sim["months"], key=lambda m: m["intake"])["month"]
    month_name = {"Feb": "February", "Mar": "March", "Apr": "April"}.get(peak_intake, peak_intake)
    nxt = forecast["rows"][0]
    return [
        gap("sadabad"), gap("sikandra-rao"), full("sasni"),
        {"icon": "🌾", "text": f"{month_name} harvest peak", "tone": "neutral"},
        gap("mursan"), full("hathras"),
        {"icon": "📈", "text": f"{nxt['season']}: {nxt['production_t'] / 1e6:.2f}M T forecast", "tone": "neutral"},
        {"icon": "❄️", "text": f"Peak strain {sim['peak_utilisation'] * 100:.0f}% in {sim['peak_month']}", "tone": "bad" if sim["peak_utilisation"] > 1 else "warn"},
    ]
