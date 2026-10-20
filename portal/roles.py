"""Role-based workspaces: the same engine, framed for each user's job."""
from __future__ import annotations

from .core import dataset as ds
from .core.analytics import compare_models, mean
from .core.geo import distance_matrix
from .scenario import hathras_scenario

# Cold storage contacts for the "Contact storage facility" buttons. ColdFlow has no
# verified directory yet, so this is empty and the workspace says so. Add entries as
# {"name", "block_id", "phone"} (from the UP Horticulture cold storage registry or the
# operators themselves) and call/WhatsApp buttons appear for that block.
FACILITY_CONTACTS: list[dict] = []

# Traffic-light wording for block status (levels come from core.storage.block_strain).
SPACE_STATUS = {
    "good": {"light": "green", "label": "Space available", "hi": "जगह उपलब्ध"},
    "warning": {"light": "yellow", "label": "Filling up", "hi": "भर रहा है"},
    "serious": {"light": "red", "label": "Nearly full", "hi": "लगभग भरा"},
    "critical": {"light": "red", "label": "Full at peak", "hi": "पीक पर भरा"},
}

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
    next_fc = cm[cm["primary"]]["rows"][0]
    return {
        "role": role,
        "meta": ROLES[role],
        "scenario": sc,
        "most_strained": by_strain[:3],
        "most_spare": spare[:3],
        "book_before": watch["month"] if watch else None,
        "five_year_avg_t": five_yr,
        "next_forecast": next_fc,
        "forecast_model": cm["primary"],
        "expansion_t": sim["capacity_needed_threshold_t"] - sc["inputs"]["total_capacity"],
        "spoilage_risk_t": sim["total_overflow_t"],
        **_field_view(sc, thr),
    }


def _field_view(sc: dict, thr: float) -> dict:
    """Plain-language view of the scenario for farmers, FPOs and store owners.

    Display only: every number is taken from the scenario as computed; nothing new is modelled.
    """
    sim, blocks = sc["simulation"], sc["blocks"]
    space = []
    for b in sorted(blocks, key=lambda b: b["name"]):
        peak = max(b["monthly"], key=lambda m: m["utilisation"])
        space.append({
            "id": b["id"], "name": b["name"], "lat": b["lat"], "lng": b["lng"],
            "level": b["level"], **SPACE_STATUS[b["level"]],
            "utilisation": b["utilisation"], "spare_t": max(b["gap_t"], 0), "short_t": max(-b["gap_t"], 0),
            "peak_month": peak["month"], "nearest": b["nearest_headroom"][:2],
            "contacts": [c for c in FACILITY_CONTACTS if c.get("block_id") == b["id"]],
        })
    months = [{"month": m["month"], "utilisation": m["utilisation"],
               "level": "critical" if m["utilisation"] > 1 else "serious" if m["utilisation"] >= thr
               else "warning" if m["utilisation"] >= thr - 0.15 else "good"} for m in sim["months"]]
    overflow = sorted([s for s in space if s["short_t"] > 0], key=lambda s: -s["short_t"])
    return {
        "space": space,
        "months": months,
        "peak_month": sim["peak_month"],
        "distances": distance_matrix(blocks),
        "overflow": overflow,
        "contacts_available": bool(FACILITY_CONTACTS),
    }
