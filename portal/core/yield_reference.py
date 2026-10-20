"""Reference dataset: Hathras potato yield and weather indices (Potato_Study, 2005-06 to 2020-21).

Kept separate from ColdFlow's production series (core/dataset.py). Yield here is
tonnes per hectare; this file has no cultivated-area data, so it must not be turned
into production tonnes or merged into PRODUCTION_SERIES. Nothing in the app's
forecasts, planner or UI reads this module; it exists for validation and analysis.
See portal/data/hathras_yield/README.md for provenance and caveats.
"""
from __future__ import annotations

import csv
import math
import os
import re

from . import dataset as ds

PATH = os.path.join(os.path.dirname(__file__), "..", "data", "hathras_yield", "hathras_yield_weather_indices.csv")
SEASON_RE = re.compile(r"^(\d{4})-(\d{2})$")
YIELD_PLAUSIBLE_T_HA = (10.0, 50.0)   # same sanity band ColdFlow uses for user data


def load(path: str = PATH) -> list[dict]:
    """Rows with numeric fields as float (time_index as int). Raises on unreadable values."""
    with open(path, newline="") as f:
        rows = []
        for raw in csv.DictReader(f):
            row = {"season": raw["season"], "time_index": int(raw["time_index"])}
            for k, v in raw.items():
                if k not in ("season", "time_index"):
                    row[k] = float(v) if v not in ("", None) else None
            rows.append(row)
    return rows


def z_columns(rows: list[dict]) -> list[str]:
    return [k for k in rows[0] if re.fullmatch(r"Z\d+", k)]


def validate(rows: list[dict]) -> dict:
    """Missing values, duplicates, types, season format/continuity, plausibility, duplicate columns."""
    cols = [k for k in rows[0]]
    missing = {k: sum(1 for r in rows if r[k] is None or (isinstance(r[k], float) and math.isnan(r[k]))) for k in cols}
    seasons = [r["season"] for r in rows]
    bad_format = [s for s in seasons if not (m := SEASON_RE.match(s)) or (int(m.group(1)) + 1) % 100 != int(m.group(2))]
    starts = sorted(int(s[:4]) for s in seasons if SEASON_RE.match(s))
    gaps = [f"{a}->{b}" for a, b in zip(starts, starts[1:]) if b != a + 1]
    times = [r["time_index"] for r in rows]
    yields = [r["yield_t_ha"] for r in rows]
    zc = z_columns(rows)
    identical = [(a, b) for i, a in enumerate(zc) for b in zc[i + 1:] if all(r[a] == r[b] for r in rows)]
    lo, hi = YIELD_PLAUSIBLE_T_HA
    return {
        "rows": len(rows),
        "columns": len(cols),
        "missing_cells": sum(missing.values()),
        "duplicate_seasons": len(seasons) - len(set(seasons)),
        "duplicate_rows": len(rows) - len({tuple(r.values()) for r in rows}),
        "bad_season_format": bad_format,
        "season_gaps": gaps,
        "time_index_consecutive": times == list(range(times[0], times[0] + len(times))),
        "coverage": (seasons[0], seasons[-1]) if seasons else None,
        "yield_range_t_ha": (min(yields), max(yields)),
        "yield_out_of_band": [r["season"] for r in rows if not (lo <= r["yield_t_ha"] <= hi)],
        "identical_columns": identical,
    }


def compare_with_coldflow(rows: list[dict]) -> list[dict]:
    """Overlapping seasons vs ColdFlow's yield (production ÷ area). Reports; never replaces."""
    cf = {r["season"]: r for r in ds.PRODUCTION_SERIES}
    out = []
    for r in rows:
        c = cf.get(r["season"])
        if not c:
            continue
        cf_t_ha = c["production_t"] / c["area_ha"]
        out.append({
            "season": r["season"],
            "reference_yield_t_ha": r["yield_t_ha"],
            "coldflow_yield_t_ha": cf_t_ha,
            "coldflow_yield_kg_ha_stated": c["yield_kg_ha"],
            "difference_t_ha": r["yield_t_ha"] - cf_t_ha,
            "difference_pct": (r["yield_t_ha"] - cf_t_ha) / cf_t_ha,
        })
    return out
