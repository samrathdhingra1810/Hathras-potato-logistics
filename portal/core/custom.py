"""User-supplied data: validation and the full analysis for any district or facility.

Errors stop the analysis; warnings flag inputs that are allowed but look unusual
(they are shown next to the results so entered data is never mistaken for
official figures).
"""
from __future__ import annotations

import math
import re

from . import dataset as ds
from .analytics import compare_models, forecast_series, summary, with_yoy
from .storage import facility_coverage, holding_economics, simulate_storage_year, storage_demand, MONTHS

SEASON_RE = re.compile(r"^(\d{4})-(\d{2})$")
MIN_SEASONS, MAX_SEASONS = 3, 30
# Plausible potato yield band (t/ha). Outside it we warn, not reject.
YIELD_WARN_LOW, YIELD_WARN_HIGH = 10.0, 50.0


class InputError(ValueError):
    """Raised with a list of human-readable problems."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def _number(v, field, errors, *, lo=0.0, hi=1e10, allow_zero=False):
    try:
        x = float(v)
    except (TypeError, ValueError):
        errors.append(f"{field} must be a number.")
        return None
    if not math.isfinite(x) or x < lo or x > hi or (x == 0 and not allow_zero):
        errors.append(f"{field} is out of range.")
        return None
    return x


def _profile(raw, default, label, errors, warnings):
    """Month -> share. Accepts fractions or percentages; normalises to sum 1."""
    if not raw:
        return dict(default)
    out = {}
    for m in MONTHS:
        v = raw.get(m, 0) if isinstance(raw, dict) else 0
        try:
            x = float(v or 0)
        except (TypeError, ValueError):
            errors.append(f"{label} for {m} must be a number.")
            return dict(default)
        if x < 0 or not math.isfinite(x):
            errors.append(f"{label} for {m} can't be negative.")
            return dict(default)
        if x:
            out[m] = x
    total = sum(out.values())
    if total <= 0:
        errors.append(f"{label} needs at least one month above zero.")
        return dict(default)
    if total > 1.5:  # entered as percentages
        out = {k: v / 100 for k, v in out.items()}
        total = sum(out.values())
    if abs(total - 1) > 0.005:
        warnings.append(f"{label} added up to {total * 100:.0f}%; it was scaled to 100%.")
        out = {k: v / total for k, v in out.items()}
    return out


def validate(payload: dict) -> dict:
    """Returns clean inputs or raises InputError."""
    errors, warnings = [], []
    if not isinstance(payload, dict):
        raise InputError(["Send a JSON object."])

    name = str(payload.get("name") or "My district").strip()[:80] or "My district"

    rows = payload.get("series")
    if not isinstance(rows, list):
        raise InputError(["Add at least three seasons of data."])
    series = []
    for i, r in enumerate(rows, start=1):
        if not isinstance(r, dict):
            errors.append(f"Row {i} is not valid.")
            continue
        season = str(r.get("season", "")).strip()
        m = SEASON_RE.match(season)
        if not m or (int(m.group(1)) + 1) % 100 != int(m.group(2)):
            errors.append(f"Row {i}: season must look like 2023-24.")
            continue
        area = _number(r.get("area_ha"), f"Row {i} area", errors, hi=1e8)
        prod = _number(r.get("production_t"), f"Row {i} production", errors, hi=1e9)
        if area is None or prod is None:
            continue
        series.append({"season": season, "area_ha": area, "production_t": prod,
                       "yield_kg_ha": prod * 1000 / area})

    if len(series) < MIN_SEASONS and not errors:
        errors.append(f"Add at least {MIN_SEASONS} seasons of data.")
    if len(series) > MAX_SEASONS:
        errors.append(f"Use at most {MAX_SEASONS} seasons.")

    series.sort(key=lambda r: r["season"])
    for a, b in zip(series, series[1:]):
        if a["season"] == b["season"]:
            errors.append(f"Season {a['season']} appears twice.")
        elif int(b["season"][:4]) != int(a["season"][:4]) + 1:
            errors.append(f"Seasons must be consecutive: {a['season']} is followed by {b['season']}.")

    for r in series:
        t_ha = r["yield_kg_ha"] / 1000
        if not (YIELD_WARN_LOW <= t_ha <= YIELD_WARN_HIGH):
            warnings.append(f"{r['season']}: yield of {t_ha:.1f} t/ha is unusual for potato. Check area and production units (ha, tonnes).")

    capacity = _number(payload.get("capacity", ds.DEFAULT_REGIONAL_CAPACITY_T), "Storage capacity", errors, hi=1e9)
    ratio = _number(payload.get("ratio", ds.DEFAULT_STORAGE_RATIO), "Share stored", errors, lo=0.01, hi=1)
    threshold = _number(payload.get("threshold", ds.DEFAULT_ALERT_THRESHOLD), "Alert threshold", errors, lo=0.5, hi=1)
    facility = _number(payload.get("facility", 10_000), "Facility capacity", errors, hi=1e9)
    intake = _profile(payload.get("intake_profile"), ds.MONTHLY_INTAKE_PROFILE, "Intake calendar", errors, warnings)
    release = _profile(payload.get("release_profile"), ds.MONTHLY_RELEASE_PROFILE, "Release calendar", errors, warnings)

    if errors:
        raise InputError(errors)

    return {
        "name": name, "series": series, "capacity": capacity, "ratio": ratio, "threshold": threshold,
        "facility": facility, "intake_profile": intake, "release_profile": release,
        "season": str(payload.get("season") or ""), "warnings": warnings,
    }


def analyse(payload: dict) -> dict:
    """Validate then run summary, forecast and storage simulation."""
    v = validate(payload)
    series = v["series"]
    fc = forecast_series(series, 2)
    seasons = {series[-1]["season"]: series[-1]["production_t"]}
    seasons.update({r["season"]: r["production_t"] for r in fc["rows"]})
    season = v["season"] if v["season"] in seasons else series[-1]["season"]
    from ..scenario import whatif_inputs  # local import: scenario imports this module's siblings

    w = whatif_inputs(payload)
    base_production = seasons[season]
    production = base_production * (1 + w["yield_shock"])
    total_capacity = v["capacity"] + w["extra_capacity"]
    demand = storage_demand(production, v["ratio"])
    sim = simulate_storage_year(demand_t=demand, capacity_t=total_capacity, alert_threshold=v["threshold"],
                                intake_profile=v["intake_profile"], release_profile=v["release_profile"])
    head = summary(series)
    return {
        "name": v["name"],
        "inputs": {**{k: v[k] for k in ("capacity", "ratio", "threshold", "facility", "intake_profile", "release_profile")},
                   "season": season, **w, "total_capacity": total_capacity},
        "base_production_t": base_production,
        "economics": holding_economics(sim, kwh_per_t_month=w["kwh"], tariff_rs_kwh=w["tariff"],
                                       tariff_change=w["tariff_change"]),
        "seasons": [{"value": s, "label": f"{s} {'actual' if s == series[-1]['season'] else 'forecast'}"} for s in seasons],
        "series": with_yoy(series),
        "summary": {k: head[k] for k in ("cagr", "avg_yield_kg_ha", "area_growth", "yield_growth")},
        "forecast": fc,
        "forecast_compare": {k: v for k, v in compare_models(series, 2).items() if k != "linear"},
        "production_t": production,
        "demand_t": demand,
        "facility_coverage": facility_coverage(v["facility"], demand),
        "district_coverage": total_capacity / demand if demand else None,
        "facilities_to_close_gap": max(demand - total_capacity, 0) / v["facility"],
        "simulation": sim,
        "warnings": v["warnings"],
    }


def hathras_example() -> dict:
    """The Hathras baseline in the custom-input shape, used as the starter dataset."""
    return {
        "name": "Hathras district (example)",
        "series": [{"season": r["season"], "area_ha": r["area_ha"], "production_t": r["production_t"]}
                   for r in ds.PRODUCTION_SERIES],
        "capacity": ds.DEFAULT_REGIONAL_CAPACITY_T,
        "ratio": ds.DEFAULT_STORAGE_RATIO,
        "threshold": ds.DEFAULT_ALERT_THRESHOLD,
        "facility": 10_000,
        "intake_profile": dict(ds.MONTHLY_INTAKE_PROFILE),
        "release_profile": dict(ds.MONTHLY_RELEASE_PROFILE),
        "yield_shock": 0, "extra_capacity": 0, "tariff_change": 0,
        "tariff": ds.DEFAULT_TARIFF_RS_KWH, "kwh": ds.DEFAULT_KWH_PER_T_MONTH,
    }
