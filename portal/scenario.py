"""Hathras baseline scenario used by the regional pages and /api/scenario."""
from __future__ import annotations

from .core import dataset as ds
from .core.analytics import forecast_series, season_status, with_yoy
from .core.geo import nearest_with_headroom
from .core.storage import (block_monthly, block_strain, facility_coverage, holding_economics,
                           simulate_storage_year, storage_demand)


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
    w = whatif_inputs(source)

    base_production = seasons[season]
    production = base_production * (1 + w["yield_shock"])
    total_capacity = capacity + w["extra_capacity"]
    demand = storage_demand(production, ratio)
    sim = simulate_storage_year(demand_t=demand, capacity_t=total_capacity, alert_threshold=threshold,
                                intake_profile=ds.MONTHLY_INTAKE_PROFILE, release_profile=ds.MONTHLY_RELEASE_PROFILE)
    blocks = block_strain(ds.BLOCKS, demand_t=demand, capacity_t=total_capacity, alert_threshold=threshold)
    blocks = block_monthly(blocks, sim)
    for b in blocks:
        b["nearest_headroom"] = nearest_with_headroom(b, blocks)
    return {
        "inputs": {"season": season, "ratio": ratio, "capacity": capacity, "threshold": threshold, "facility": facility,
                   **w, "total_capacity": total_capacity},
        "base_production_t": base_production,
        "economics": holding_economics(sim, kwh_per_t_month=w["kwh"], tariff_rs_kwh=w["tariff"],
                                       tariff_change=w["tariff_change"]),
        "seasons": [{"value": s, "label": f"{s} {'actual' if s == series[-1]['season'] else season_status(s)['status']}"} for s in seasons],
        "production_t": production,
        "demand_t": demand,
        "facility_coverage": facility_coverage(facility, demand),
        "district_coverage": total_capacity / demand if demand else None,
        "facilities_to_close_gap": sim["capacity_gap_t"] / facility,
        "simulation": sim,
        "blocks": blocks,
    }


def whatif_inputs(source) -> dict:
    """What-if levers shared by the Hathras planner and the own-data planner."""
    return {
        "yield_shock": num_arg(source, "yield_shock", 0.0, -0.6, 0.6),
        "extra_capacity": num_arg(source, "extra_capacity", 0.0, 0, 1e8),
        "tariff_change": num_arg(source, "tariff_change", 0.0, -0.9, 3),
        "kwh": num_arg(source, "kwh", ds.DEFAULT_KWH_PER_T_MONTH, 0.1, 100),
        "tariff": num_arg(source, "tariff", ds.DEFAULT_TARIFF_RS_KWH, 0.1, 100),
    }
