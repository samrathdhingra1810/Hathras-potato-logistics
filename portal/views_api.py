"""JSON API: baseline data, forecasts, scenarios, own-data analysis, saved plans."""
from __future__ import annotations

import json

from flask import Response, current_app, g, jsonify, request

from . import assistant, db, sheets
from .core import dataset as ds
from .core import external_sources as xs
from .core.analytics import forecast_series, with_yoy
from .core.custom import InputError, analyse, validate
from .core.allocation import allocate
from .scenario import hathras_scenario, num_arg

MAX_PLANS_PER_USER = 50
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _require_user():
    if not db.accounts_enabled():
        return jsonify(error="Accounts aren't available on this deployment."), 503
    if g.get("user") is None:
        return jsonify(error="Sign in to save plans."), 401
    return None


def _plan_payload(body):
    """Validates a plan body; returns (name, payload_json) or raises InputError."""
    payload = body.get("payload") if isinstance(body, dict) else None
    validate(payload)  # raises InputError with readable messages
    name = str(body.get("name") or payload.get("name") or "Untitled plan").strip()[:80] or "Untitled plan"
    return name, json.dumps(payload, separators=(",", ":"))


def init_app(app):
    @app.get("/api/health")
    def api_health():
        return jsonify(ok=True, accounts=db.accounts_enabled())

    @app.get("/api/sources/up-districts")
    def api_up_districts():
        """UP district potato production, crop year 2022-23 (secondary source, unverified)."""
        return jsonify(source=xs.DISTRICT_SOURCE, validation=xs.validate_districts(),
                       hathras_vs_coldflow=xs.compare_hathras(), rows=list(xs.districts()))

    @app.get("/api/sources/nhb-cold-storage")
    def api_nhb_cold_storage():
        """Historical NHB-sanctioned cold storage projects (2000-2012). ?district=Hathras (default) or ?district=all."""
        want = (request.args.get("district") or "Hathras").strip()
        rows = [r for r in xs.nhb_projects() if want.lower() == "all" or r["district"].lower() == want.lower()]
        return jsonify(source=xs.NHB_SOURCE, district=want, count=len(rows),
                       note="Sanctioned capacity from historical subsidy records, not current capacity or availability.",
                       rows=rows)

    @app.get("/api/baseline")
    def api_baseline():
        return jsonify(district=ds.DISTRICT, source=ds.DATA_SOURCE, series=with_yoy(ds.PRODUCTION_SERIES),
                       blocks=ds.BLOCKS, assumptions=ds.ASSUMPTIONS)

    @app.get("/api/forecast")
    def api_forecast():
        horizon = int(num_arg(request.args, "horizon", 2, 1, 5))
        return jsonify(forecast_series(ds.PRODUCTION_SERIES, horizon))

    @app.route("/api/scenario", methods=["GET", "POST"])
    def api_scenario():
        source = (request.get_json(silent=True) or {}) if request.method == "POST" else request.args
        return jsonify(hathras_scenario(source))

    @app.get("/api/allocation")
    def api_allocation():
        """Peak-season redistribution between Hathras blocks (modelled block split, straight-line km)."""
        sc = hathras_scenario(request.args)
        max_km = num_arg(request.args, "max_km", 0, 0, 500) or None
        road_factor = num_arg(request.args, "road_factor", 1.0, 1.0, 3.0)
        rate = num_arg(request.args, "rate", 0, 0, 10_000)
        nodes = [{"id": b["id"], "name": b["name"], "lat": b["lat"], "lng": b["lng"],
                  "demand_t": b["demand_t"], "capacity_t": b["capacity_t"]} for b in sc["blocks"]]
        out = allocate(nodes, max_km=max_km, road_factor=road_factor)
        if out.get("ok"):
            out["rate_rs_per_tkm"] = rate or None
            out["freight_cost_rs"] = out["tonne_km"] * rate if rate else None
            out["season"] = sc["inputs"]["season"]
            out["data_basis"] = ("Demo on modelled data: block demand and capacity use the assumed block split; "
                                 "distances are straight-line between block HQs" +
                                 (f" × road factor {road_factor:g}" if road_factor != 1 else "") + ".")
        return jsonify(out), (200 if out.get("ok") else 503)

    @app.post("/api/analyse")
    def api_analyse():
        try:
            return jsonify(analyse(request.get_json(silent=True)))
        except InputError as e:
            return jsonify(errors=e.errors), 422

    # ---- Import / export ----
    @app.get("/templates/coldflow-template.csv")
    def template_csv():
        return Response(sheets.template_csv(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=coldflow-template.csv"})

    @app.get("/templates/coldflow-template.xlsx")
    def template_xlsx():
        return Response(sheets.template_xlsx(), mimetype=XLSX,
                        headers={"Content-Disposition": "attachment; filename=coldflow-template.xlsx"})

    @app.post("/api/import")
    def api_import():
        f = request.files.get("file")
        if f is None:
            return jsonify(errors=["Choose a .csv or .xlsx file."]), 400
        try:
            return jsonify(sheets.parse_upload(f.filename, f.read()))
        except sheets.ImportError_ as e:
            return jsonify(errors=[str(e)]), 422

    @app.post("/api/export")
    def api_export():
        body = request.get_json(silent=True) or {}
        kind = body.get("kind")
        try:
            if kind == "plan":
                a = analyse(body.get("payload"))
                title, blocks = a["name"], None
            elif kind == "hathras":
                a = hathras_scenario(body.get("params") or {})
                a["series"] = with_yoy(ds.PRODUCTION_SERIES)
                title, blocks = f"Hathras district · {a['inputs']['season']}", a["blocks"]
            else:
                return jsonify(errors=["Unknown report type."]), 400
        except InputError as e:
            return jsonify(errors=e.errors), 422
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in title.lower()).strip("-")[:60] or "report"
        return Response(sheets.report_xlsx(title, a, blocks=blocks), mimetype=XLSX,
                        headers={"Content-Disposition": f"attachment; filename=coldflow-{safe}.xlsx"})

    @app.post("/api/assistant")
    def api_assistant():
        body = request.get_json(silent=True) or {}
        ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "?").split(",")[0].strip()
        if not assistant.allow(ip):
            return jsonify(error="You're sending questions quickly. Wait a few minutes and try again."), 429
        try:
            history = assistant.clean_history(body.get("messages"))
        except ValueError as e:
            return jsonify(error=str(e)), 400
        if not assistant.ai_configured():
            return jsonify(assistant.answer_offline(history, body.get("context")))
        try:
            return jsonify(assistant.answer_with_gemini(history, body.get("context")))
        except Exception:
            current_app.logger.exception("assistant request failed")
            fallback = assistant.answer_offline(history)
            fallback["reply"] = fallback["reply"].replace(
                "_Offline help: the AI assistant isn't connected on this site yet._",
                "_The AI assistant couldn't be reached, so this is offline help._")
            return jsonify(fallback)

    # ---- Saved plans (signed-in users) ----
    @app.get("/api/plans")
    def api_plans():
        if (err := _require_user()):
            return err
        rows = db.get_db().all("SELECT id, name, created_at, updated_at FROM plans WHERE user_id = ? ORDER BY updated_at DESC",
                               (g.user["id"],))
        return jsonify(plans=rows)

    @app.post("/api/plans")
    def api_plan_create():
        if (err := _require_user()):
            return err
        try:
            name, payload = _plan_payload(request.get_json(silent=True))
        except InputError as e:
            return jsonify(errors=e.errors), 422
        conn = db.get_db()
        count = conn.one("SELECT COUNT(*) AS n FROM plans WHERE user_id = ?", (g.user["id"],))["n"]
        if count >= MAX_PLANS_PER_USER:
            return jsonify(errors=[f"You can keep up to {MAX_PLANS_PER_USER} plans. Delete one to save another."]), 422
        ts = db.now()
        pid = conn.insert("INSERT INTO plans (user_id, name, payload, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                          (g.user["id"], name, payload, ts, ts))
        conn.commit()
        return jsonify(id=pid, name=name, updated_at=ts), 201

    @app.put("/api/plans/<int:plan_id>")
    def api_plan_update(plan_id):
        if (err := _require_user()):
            return err
        try:
            name, payload = _plan_payload(request.get_json(silent=True))
        except InputError as e:
            return jsonify(errors=e.errors), 422
        conn = db.get_db()
        ts = db.now()
        cur = conn.execute("UPDATE plans SET name = ?, payload = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                           (name, payload, ts, plan_id, g.user["id"]))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify(error="Plan not found."), 404
        return jsonify(id=plan_id, name=name, updated_at=ts)

    @app.route("/api/<path:_rest>", methods=["GET", "POST", "PUT", "DELETE"])
    def api_not_found(_rest):
        return jsonify(error="Not found"), 404
