"""Hathras baseline scenario used by the regional pages and /api/scenario."""
from __future__ import annotations

from .core import dataset as ds
from .core.analytics import forecast_series, with_yoy
from .core.storage import block_strain, facility_coverage, simulate_storage_year, storage_demand


def num_arg(source, key, default, lo, hi):
    """Reads a bounded number; falls back to default when missing, malformed or out of range."""
    try:
        v = float(source.get(key, default))
    except (TypeError, ValueError):
        return default
    return v if lo <= v <= hi else default


def hathras_scenario(source) -> dict:
    """Planner inputs -> demand, simulation and block strain for one Hathras season."""
    series = with_yoy(ds.PRODUCTION_SERIES)
    fc = forecast_series(ds.PRODUCTION_SERIES, 2)
    seasons = {series[-1]["season"]: series[-1]["production_t"]}
    seasons.update({r["season"]: r["production_t"] for r in fc["rows"]})

    season = source.get("season") or series[-1]["season"]
    if season not in seasons:
        season = series[-1]["season"]
    ratio = num_arg(source, "ratio", ds.DEFAULT_STORAGE_RATIO, 0.05, 1)
    capacity = num_arg(source, "capacity", ds.DEFAULT_REGIONAL_CAPACITY_T, 1, 1e8)
    threshold = num_arg(source, "threshold", ds.DEFAULT_ALERT_THRESHOLD, 0.5, 1)
    facility = num_arg(source, "facility", 10_000, 1, 1e7)

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
