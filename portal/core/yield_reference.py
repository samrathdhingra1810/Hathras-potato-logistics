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


# ---------------------------------------------------------------- chronological backtest

BACKTEST_MIN_TRAIN = 8          # seasons in the first training window (8 one-step tests)
DUPLICATE_COLUMNS = {"Z560", "Z561"}   # copies of Z460 / Z461 in the source


def _trend_plus_best(rows, o, suffix):
    """Yield ~ trend + one Z index, picking the index inside the training window only."""
    import numpy as np
    cols = [c for c in z_columns(rows) if c.endswith(suffix) and c not in DUPLICATE_COLUMNS]
    y = np.array([r["yield_t_ha"] for r in rows[:o]])
    t = np.arange(o)
    resid = y - np.polyval(np.polyfit(t, y, 1), t)
    best = max(cols, key=lambda c: abs(np.corrcoef([r[c] for r in rows[:o]], resid)[0, 1]))
    a = np.c_[np.ones(o), t, [r[best] for r in rows[:o]]]
    b = np.linalg.lstsq(a, y, rcond=None)[0]
    return float(b @ [1, o, rows[o][best]])


def _ridge_unweighted(rows, o, lambdas=(0.1, 1, 10, 100, 1000)):
    """Ridge on trend + all unweighted Z indices; lambda chosen by leave-one-out inside the window."""
    import numpy as np
    cols = [c for c in z_columns(rows) if c.endswith("0") and c not in DUPLICATE_COLUMNS]
    feats = lambda j: [rows[j][c] for c in cols] + [j]
    y = np.array([r["yield_t_ha"] for r in rows])

    def fit(idx, lam):
        f = np.array([feats(j) for j in idx])
        mu, sd = f.mean(0), f.std(0) + 1e-12
        fs, ym = (f - mu) / sd, y[idx].mean()
        w = np.linalg.solve(fs.T @ fs + lam * np.eye(fs.shape[1]), fs.T @ (y[idx] - ym))
        return lambda j: float(ym + ((np.array(feats(j)) - mu) / sd) @ w)

    loo = lambda lam: sum(abs(fit([i for i in range(o) if i != k], lam)(k) - y[k]) for k in range(o))
    return fit(list(range(o)), min(lambdas, key=loo))(o)


WEATHER_MODELS = [
    ("trend_weather", "Trend + 1 unweighted weather index", lambda rows, o: _trend_plus_best(rows, o, "0")),
    ("trend_weather_weighted", "Trend + 1 weighted index (leakage-suspect)", lambda rows, o: _trend_plus_best(rows, o, "1")),
    ("ridge_weather", "Ridge, all unweighted indices", _ridge_unweighted),
]


def backtest(rows: list[dict], min_train: int = BACKTEST_MIN_TRAIN) -> dict:
    """One-season-ahead rolling-origin MAE (t/ha) for ColdFlow's models vs weather models.

    For each origin o the models see seasons [0, o) only; weather models also use
    season o's weather indices, which exist once the Oct–Jan growing weeks are over
    (i.e. before harvest), but never its yield.
    """
    from .evaluation import MODELS
    y = [r["yield_t_ha"] for r in rows]
    errors = {}
    for o in range(min_train, len(rows)):
        for key, _label, _kind, fn in MODELS:
            errors.setdefault(key, []).append(fn(y[:o], 1)[0] - y[o])
        for key, _label, fn in WEATHER_MODELS:
            errors.setdefault(key, []).append(fn(rows, o) - y[o])
    labels = {k: lab for k, lab, _kind, _f in MODELS} | {k: lab for k, lab, _f in WEATHER_MODELS}
    naive = sum(abs(e) for e in errors["naive"]) / len(errors["naive"])
    out = {}
    for key, errs in errors.items():
        mae = sum(abs(e) for e in errs) / len(errs)
        out[key] = {"label": labels[key], "n": len(errs), "mae_t_ha": mae, "skill_vs_naive": 1 - mae / naive,
                    "bias_t_ha": sum(errs) / len(errs)}
    return {"targets": (rows[min_train]["season"], rows[-1]["season"]), "models": out}
