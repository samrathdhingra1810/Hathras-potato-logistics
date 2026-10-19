"""Cold storage demand, coverage and monthly stock-vs-capacity modelling."""
from __future__ import annotations

import math

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PEAK_HARVEST_MONTHS = ("Feb", "Mar", "Apr")


def storage_demand(production_t: float, storage_ratio: float) -> float:
    return production_t * storage_ratio


def facility_coverage(facility_capacity_t: float, demand_t: float) -> float:
    """Share of regional demand that one facility's capacity covers."""
    return facility_capacity_t / demand_t if demand_t > 0 else 0.0


def strain_level(utilisation: float, alert_threshold: float = 0.9) -> str:
    if utilisation > 1:
        return "critical"
    if utilisation >= alert_threshold:
        return "serious"
    if utilisation >= alert_threshold - 0.15:
        return "warning"
    return "good"


def simulate_storage_year(*, demand_t, capacity_t, intake_profile, release_profile, alert_threshold=0.9) -> dict:
    """Simulates stock through the calendar year.

    Intake follows intake_profile and releases follow release_profile. Intake that
    would exceed capacity is overflow: produce with no cold chain slot. A parallel
    unconstrained stock shows what the season would hold with unlimited capacity.
    """
    stock = 0.0
    unconstrained = 0.0
    cumulative_overflow = 0.0
    months = []
    for month in MONTHS:
        intake = demand_t * intake_profile.get(month, 0)
        accepted = min(intake, max(capacity_t - stock, 0))
        overflow = intake - accepted
        cumulative_overflow += overflow

        stock += accepted
        unconstrained += intake
        peak_stock = stock  # end of loading, before this month's releases
        demanded = unconstrained

        scheduled = demand_t * release_profile.get(month, 0)
        release = min(stock, scheduled)
        stock -= release
        unconstrained -= min(unconstrained, scheduled)

        utilisation = demanded / capacity_t if capacity_t > 0 else math.inf
        months.append({
            "month": month,
            "intake": intake,
            "accepted": accepted,
            "overflow": overflow,
            "release": release,
            "stock": peak_stock,
            "demanded_stock": demanded,
            "unmet": max(demanded - peak_stock, 0) if overflow > 0 else 0.0,
            "cumulative_overflow": cumulative_overflow,
            "utilisation": utilisation,
            "level": strain_level(utilisation, alert_threshold),
            "peak_harvest": month in PEAK_HARVEST_MONTHS,
        })

    peak = max(months, key=lambda m: m["demanded_stock"])
    return {
        "months": months,
        "peak_month": peak["month"],
        "peak_utilisation": peak["utilisation"],
        "total_overflow_t": cumulative_overflow,
        "deficit_months": [m["month"] for m in months if m["overflow"] > 0],
        "alert_months": [m["month"] for m in months if m["peak_harvest"] and m["utilisation"] >= alert_threshold],
        "status": strain_level(peak["utilisation"], alert_threshold),
    }


def block_strain(blocks, *, demand_t, capacity_t, alert_threshold=0.9) -> list[dict]:
    """Splits district demand and capacity across blocks and scores each block."""
    out = []
    for b in blocks:
        d = demand_t * b["production_share"]
        c = capacity_t * b["capacity_share"]
        u = d / c if c > 0 else math.inf
        out.append({**b, "demand_t": d, "capacity_t": c, "gap_t": c - d, "utilisation": u,
                    "level": strain_level(u, alert_threshold)})
    return out
