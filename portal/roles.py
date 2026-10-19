"""Role-based workspaces: the same engine, framed for each user's job."""
from __future__ import annotations

from .core import dataset as ds
from .core.analytics import compare_models, mean
from .scenario import hathras_scenario

ROLES = {
    "owner": {
        "label": "Cold storage owner",
        "short": "Storage owner",
        "tagline": "Utilisation, holding costs and where demand will come from.",
        "prompts": [
            "How full will district cold storage be each month this season?",
            "What would a 15% electricity tariff rise do to holding costs?",
            "Recommend optimal capacity expansion for next season.",
        ],
    },
    "fpo": {
        "label": "Farmer / FPO",
        "short": "Farmer / FPO",
        "tagline": "When to book space, and where storage is still available.",
        "prompts": [
            "When should I book cold storage space before it fills up?",
            "Which blocks near Sasni still have spare storage?",
            "Compare this year's harvest forecast with the 5-year average.",
        ],
    },
    "admin": {
        "label": "District administrator",
        "short": "District admin",
        "tagline": "Deficit tracking, spoilage risk and where new capacity helps most.",
        "prompts": [
            "Which blocks face the highest shortage risk in April?",
            "How much produce is at spoilage risk without new capacity?",
            "Recommend optimal capacity expansion for next season.",
        ],
    },
}


def workspace_data(role: str) -> dict:
    sc = hathras_scenario({})
    sim, blocks = sc["simulation"], sc["blocks"]
    thr = sc["inputs"]["threshold"]
    by_strain = sorted(blocks, key=lambda b: -b["utilisation"])
    spare = sorted([b for b in blocks if b["gap_t"] > 0], key=lambda b: -b["gap_t"])
    # First month the district crosses the watch level, i.e. book before this.
    watch = next((m for m in sim["months"] if m["utilisation"] >= thr - 0.15), None)
    cm = compare_models(ds.PRODUCTION_SERIES)
    five_yr = mean(r["production_t"] for r in ds.PRODUCTION_SERIES[-5:])
    next_fc = cm[cm["recommended"]]["rows"][0]
    return {
        "role": role,
        "meta": ROLES[role],
        "scenario": sc,
        "most_strained": by_strain[:3],
        "most_spare": spare[:3],
        "book_before": watch["month"] if watch else None,
        "five_year_avg_t": five_yr,
        "next_forecast": next_fc,
        "forecast_model": cm["recommended"],
        "expansion_t": sim["capacity_needed_threshold_t"] - sc["inputs"]["total_capacity"],
        "spoilage_risk_t": sim["total_overflow_t"],
    }
