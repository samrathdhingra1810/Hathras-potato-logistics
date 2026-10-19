"""District registry. Only districts with verified figures are loaded.

To add a district, append an entry with its season series and a source note.
Candidates are listed so the UI can show what's planned, but they carry no
numbers until a verified dataset (e.g. UP Horticulture / DES APY, NHB) is added.
"""
from __future__ import annotations

from . import dataset as ds

LOADED = {
    "hathras": {
        "name": "Hathras",
        "state": "Uttar Pradesh",
        "source": ds.DATA_SOURCE["label"],
        "series": [{"season": r["season"], "area_ha": r["area_ha"], "production_t": r["production_t"]}
                   for r in ds.PRODUCTION_SERIES],
        "capacity": ds.DEFAULT_REGIONAL_CAPACITY_T,
    },
}

CANDIDATES = ["Agra", "Aligarh", "Firozabad", "Farrukhabad", "Kannauj", "Mainpuri", "Etawah"]


def listing() -> dict:
    return {
        "loaded": [{"id": k, "name": v["name"], "state": v["state"], "source": v["source"]} for k, v in LOADED.items()],
        "candidates": CANDIDATES,
    }


def payload_for(district_id: str) -> dict | None:
    d = LOADED.get(district_id)
    if not d:
        return None
    return {"name": f"{d['name']} district", "series": d["series"], "capacity": d["capacity"]}
