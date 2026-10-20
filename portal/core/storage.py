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

    Releases are a share of what was actually loaded so far (accepted stock), not of
    total demand: overflow never entered storage, so it can't be released from it.
    With the default calendar (loading Feb-Apr, release May-Nov) this releases exactly
    the stored tonnage and ends the year at zero.
    """
    stock = 0.0
    unconstrained = 0.0
    loaded = 0.0          # cumulative tonnes accepted into storage
    loaded_demand = 0.0   # cumulative tonnes that wanted storage
    cumulative_overflow = 0.0
    months = []
    for month in MONTHS:
        start_stock = stock
        intake = demand_t * intake_profile.get(month, 0)
        accepted = min(intake, max(capacity_t - stock, 0))
        overflow = intake - accepted
        cumulative_overflow += overflow
        loaded += accepted
        loaded_demand += intake

        stock += accepted
        unconstrained += intake
        peak_stock = stock  # end of loading, before this month's releases
        demanded = unconstrained

        share = release_profile.get(month, 0)
        release = min(stock, loaded * share)
        stock -= release
        unconstrained -= min(unconstrained, loaded_demand * share)

        utilisation = demanded / capacity_t if capacity_t > 0 else math.inf
        months.append({
            "month": month,
            "intake": intake,
            "accepted": accepted,
            "overflow": overflow,
            "release": release,
            "start_stock": start_stock,
            "end_stock": stock,
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
        # Capacity at which the season's peak fits: with no deficit, and with peak at the alert threshold.
        "capacity_needed_t": peak["demanded_stock"],
        "capacity_needed_threshold_t": peak["demanded_stock"] / alert_threshold if alert_threshold else peak["demanded_stock"],
        "capacity_gap_t": max(peak["demanded_stock"] - capacity_t, 0.0),
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


def holding_economics(sim: dict, *, kwh_per_t_month: float, tariff_rs_kwh: float, tariff_change: float = 0.0) -> dict:
    """Electricity cost of holding the season's stock.

    Each month's average stock is (opening + closing) / 2, assuming loading and
    withdrawals are spread evenly through the month.
    """
    rate = tariff_rs_kwh * (1 + tariff_change)
    monthly = []
    total_t_months = 0.0
    for m in sim["months"]:
        avg = max((m["start_stock"] + m["end_stock"]) / 2, 0.0)
        total_t_months += avg
        monthly.append({"month": m["month"], "avg_stock_t": avg, "cost_rs": avg * kwh_per_t_month * rate})
    total = total_t_months * kwh_per_t_month * rate
    stored = sum(m["accepted"] for m in sim["months"])
    return {
        "rate_rs_kwh": rate,
        "kwh_per_t_month": kwh_per_t_month,
        "tonne_months": total_t_months,
        "energy_kwh": total_t_months * kwh_per_t_month,
        "season_cost_rs": total,
        "cost_per_t_stored_rs": total / stored if stored else 0.0,
        "monthly": monthly,
    }


def block_monthly(blocks_strain: list[dict], sim: dict) -> list[dict]:
    """Adds each block's utilisation per month (district stock shape scaled by the block's shares)."""
    district_peak = max(m["demanded_stock"] for m in sim["months"]) or 1.0
    out = []
    for b in blocks_strain:
        months = [{"month": m["month"], "utilisation": b["utilisation"] * m["demanded_stock"] / district_peak}
                  for m in sim["months"]]
        out.append({**b, "monthly": months})
    return out
