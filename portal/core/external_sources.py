"""External reference datasets: UP district potato production (2022-23) and the NHB
list of cold storage projects sanctioned under its subsidy scheme (2000-2012).

Both are kept separate from ColdFlow's own series (core/dataset.py) and from the
storage model. Nothing here changes a forecast, simulation or planning figure;
the pages show these records beside ColdFlow's numbers, clearly labelled.
See portal/data/up_district_potato/README.md and portal/data/nhb_cold_storage/README.md.
"""
from __future__ import annotations

import csv
import os
from functools import lru_cache

from . import dataset as ds

_DATA = os.path.join(os.path.dirname(__file__), "..", "data")
DISTRICT_CSV = os.path.join(_DATA, "up_district_potato", "up_district_potato_2022_23.csv")
NHB_CSV = os.path.join(_DATA, "nhb_cold_storage", "nhb_up_cold_storage_projects.csv")

DISTRICT_SOURCE = {
    "label": "Uttar Pradesh district potato area & production, crop year 2022-23",
    "publisher": "Indian Potato (indianpotato.com), compiled by its editorial team",
    "url": "https://indianpotato.com/uttar-pradesh-potato-production-district-wise/",
    "published": "2026-08-06", "updated": "2026-08-20", "retrieved": "2026-10-22",
    "crop_year": "2022-23",
    "status": "Secondary compilation; the original government source is not named. Unverified.",
}
NHB_SOURCE = {
    "label": "NHB capital investment subsidy: cold storage projects sanctioned in Uttar Pradesh",
    "publisher": "National Horticulture Board (NHB), Government of India",
    "url": "https://www.nhb.gov.in/doc/UP.pdf",
    "file_modified": "2013-10-08", "retrieved": "2026-10-22",
    "period": "Sanctions dated 2000 to 2012",
    "status": "Historical sanction records. Capacity is as sanctioned, not current capacity, occupancy or availability.",
}


def _num(v):
    return float(v) if v not in ("", None) else None


@lru_cache(maxsize=1)
def districts() -> tuple:
    with open(DISTRICT_CSV, newline="", encoding="utf-8") as f:
        return tuple({"crop_year": r["crop_year"], "rank": int(r["rank"]), "district": r["district"],
                      "area_ha": _num(r["area_ha"]), "production_t": _num(r["production_t"]),
                      "yield_t_ha": _num(r["yield_t_ha"]), "share_pct": _num(r["share_pct"])}
                     for r in csv.DictReader(f))


@lru_cache(maxsize=1)
def nhb_projects() -> tuple:
    out = []
    with open(NHB_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append({
                "sr": int(r["sr"]), "pdf_page": int(r["pdf_page"]), "name": r["name"], "address": r["address"],
                "district": r["district"], "district_raw": r["district_raw"], "block_hint": r["block_hint"] or None,
                "unit_type": r["unit_type"], "sanctioned_raw": r["sanctioned_raw"],
                "sanctioned_date": r["sanctioned_date"] or None,
                "sanctioned_year": int(r["sanctioned_year"]) if r["sanctioned_year"] else None,
                "capacity_mt_sanctioned": _num(r["capacity_mt"]), "capacity_mt_raw": r["capacity_mt_raw"],
                "flags": [x for x in r["flags"].split(";") if x],
            })
    return tuple(out)


def validate_districts(rows=None) -> dict:
    rows = rows or districts()
    names = [r["district"] for r in rows]
    gap = max(abs(r["area_ha"] * r["yield_t_ha"] - r["production_t"]) / r["production_t"] for r in rows)
    return {
        "rows": len(rows), "unique_districts": len(set(names)), "duplicates": len(names) - len(set(names)),
        "crop_years": sorted({r["crop_year"] for r in rows}),
        "missing_values": sum(1 for r in rows for k in ("area_ha", "production_t", "yield_t_ha") if r[k] is None),
        "total_production_t": sum(r["production_t"] for r in rows),
        "share_sum_pct": round(sum(r["share_pct"] for r in rows), 2),
        "max_area_x_yield_gap": gap,          # internal consistency of the published table
    }


def district(name: str):
    return next((r for r in districts() if r["district"].lower() == name.lower()), None)


def compare_hathras() -> dict:
    """Hathras in the 2022-23 compilation vs ColdFlow's own 2022-23 record. Reports; never replaces."""
    ext = district("Hathras")
    own = next((r for r in ds.PRODUCTION_SERIES if r["season"] == DISTRICT_SOURCE["crop_year"]), None)
    if not ext or not own:
        return {"available": False}
    own_yield = own["production_t"] / own["area_ha"]
    pct = lambda a, b: (a - b) / b
    return {
        "available": True, "season": DISTRICT_SOURCE["crop_year"],
        "external": {"area_ha": ext["area_ha"], "production_t": ext["production_t"], "yield_t_ha": ext["yield_t_ha"],
                     "rank": ext["rank"], "share_pct": ext["share_pct"]},
        "coldflow": {"area_ha": own["area_ha"], "production_t": own["production_t"], "yield_t_ha": own_yield},
        "difference_pct": {"area": pct(ext["area_ha"], own["area_ha"]),
                           "production": pct(ext["production_t"], own["production_t"]),
                           "yield": pct(ext["yield_t_ha"], own_yield)},
    }


def hathras_facilities() -> dict:
    """Historical NHB-sanctioned projects in Hathras, grouped by the block named in the address."""
    recs = [r for r in nhb_projects() if r["district"] == "Hathras"]
    usable = [r for r in recs if r["capacity_mt_sanctioned"] is not None and "capacity_implausible" not in r["flags"]]
    by_block = {}
    for b in ds.BLOCKS:
        rs = [r for r in recs if r["block_hint"] == b["id"]]
        caps = [r["capacity_mt_sanctioned"] for r in rs if r in usable]
        yrs = [r["sanctioned_year"] for r in rs if r["sanctioned_year"]]
        by_block[b["id"]] = {"records": rs, "count": len(rs), "capacity_mt_sanctioned": sum(caps),
                             "years": (min(yrs), max(yrs)) if yrs else None}
    years = [r["sanctioned_year"] for r in recs if r["sanctioned_year"]]
    return {
        "records": recs, "count": len(recs), "by_block": by_block,
        "unassigned": [r for r in recs if not r["block_hint"]],
        "flagged": [r for r in recs if r["flags"]],
        "capacity_mt_sanctioned": sum(r["capacity_mt_sanctioned"] for r in usable),
        "capacity_records": len(usable),
        "years": (min(years), max(years)) if years else None,
    }
