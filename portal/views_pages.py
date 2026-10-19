"""Public pages: landing, Hathras regional pages, own-data planner, info pages."""
from __future__ import annotations

import csv
import io
import json

from flask import Response, g, render_template, request

from . import db
from .core import dataset as ds
from .core.analytics import forecast_series, with_yoy
from .core.custom import hathras_example
from .scenario import hathras_scenario


def init_app(app):
    @app.get("/")
    def home():
        return render_template("landing.html", scenario=hathras_scenario({}),
                               forecast=forecast_series(ds.PRODUCTION_SERIES, 2))

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
                               forecast=forecast_series(ds.PRODUCTION_SERIES, 2))

    @app.get("/tools/planner")
    def tool_planner():
        return render_template("tools/planner.html", scenario=hathras_scenario(request.args))

    @app.get("/tools/map")
    def tool_map():
        return render_template("tools/map.html", scenario=hathras_scenario(request.args))

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
                               accounts=db.accounts_enabled())

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

    @app.get("/privacy")
    def privacy():
        return render_template("legal/privacy.html")

    @app.get("/terms")
    def terms():
        return render_template("legal/terms.html")
