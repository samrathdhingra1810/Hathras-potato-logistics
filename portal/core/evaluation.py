"""Rolling-origin (time-series cross-validation) evaluation of the forecast models.

For every forecast origin o (training on seasons [0, o)), each model forecasts the
next `h` seasons, and the forecast is scored against the season that actually
followed. Training windows only ever use data before the season being predicted,
so no future information leaks into a forecast.

Metrics (errors e = forecast − actual):
  MAE   = mean |e|                       (tonnes)
  WAPE  = Σ|e| / Σ actual                (share of actual volume)
  Bias  = mean e  and  Σe / Σ actual     (positive = over-forecast)
  Skill = 1 − MAE_model / MAE_naive      (positive = better than "same as last season")

Every number comes from the series passed in. With short histories the number of
evaluation points is tiny; `assess()` states that plainly instead of ranking models
as if the result were reliable.
"""
from __future__ import annotations

from .analytics import LinearModel, holt_damped, mean

MIN_TRAIN = 3          # smallest training window (linear trend and Holt need 3 points)
HORIZONS = (1, 2)
RELIABLE_POINTS = 8    # below this many one-step errors, rankings are treated as indicative only


def _naive(ys, h):
    return [ys[-1]] * h


def _drift(ys, h):
    step = (ys[-1] - ys[0]) / (len(ys) - 1)
    return [ys[-1] + step * k for k in range(1, h + 1)]


def _mean(ys, h):
    return [mean(ys)] * h


def _linear(ys, h):
    m = LinearModel(list(range(len(ys))), ys)
    return [m.predict(len(ys) - 1 + k)["value"] for k in range(1, h + 1)]


def _holt(ys, h):
    return [r["value"] for r in holt_damped(ys, h)["rows"]]


MODELS = [
    # key, label, kind, forecaster
    ("linear", "Linear trend (current model)", "model", _linear),
    ("holt", "Damped exponential smoothing", "model", _holt),
    ("drift", "Drift baseline", "baseline", _drift),
    ("naive", "Naive baseline (last season)", "baseline", _naive),
    ("mean", "Historical mean baseline", "baseline", _mean),
]
LABELS = {k: lab for k, lab, _kind, _f in MODELS}
KINDS = {k: kind for k, _lab, kind, _f in MODELS}


def rolling_origin(seasons: list[str], ys: list[float], *, min_train: int = MIN_TRAIN, horizons=HORIZONS) -> list[dict]:
    """One row per (model, origin, horizon) with forecast, actual and error."""
    rows = []
    n = len(ys)
    for o in range(min_train, n):
        train = ys[:o]
        for key, _label, _kind, fn in MODELS:
            preds = fn(train, max(horizons))
            for h in horizons:
                t = o + h - 1
                if t >= n:
                    continue
                f, a = preds[h - 1], ys[t]
                rows.append({"model": key, "origin": seasons[o - 1], "trained_on": o, "horizon": h,
                             "target": seasons[t], "forecast": f, "actual": a, "error": f - a})
    return rows


def metrics(rows: list[dict]) -> dict:
    """Aggregate metrics per model and horizon, plus skill against the naive baseline."""
    out = {}
    for key, _label, _kind, _f in MODELS:
        out[key] = {}
        for h in HORIZONS:
            sel = [r for r in rows if r["model"] == key and r["horizon"] == h]
            if not sel:
                out[key][h] = None
                continue
            abs_err = [abs(r["error"]) for r in sel]
            actual_sum = sum(r["actual"] for r in sel)
            err_sum = sum(r["error"] for r in sel)
            out[key][h] = {
                "n": len(sel),
                "mae": mean(abs_err),
                "wape": sum(abs_err) / actual_sum if actual_sum else None,
                "bias": err_sum / len(sel),
                "bias_pct": err_sum / actual_sum if actual_sum else None,
            }
    for h in HORIZONS:
        base = out["naive"].get(h)
        for key in out:
            m = out[key].get(h)
            if m and base and base["mae"]:
                m["skill_vs_naive"] = 1 - m["mae"] / base["mae"]
            elif m:
                m["skill_vs_naive"] = None
    return out


def assess(m: dict, n_seasons: int) -> dict:
    """Plain-language reliability statement derived only from the computed metrics."""
    h1 = {k: v[1] for k, v in m.items() if v.get(1)}
    if not h1:
        return {"level": "insufficient", "points": 0, "best": None, "message":
                f"With {n_seasons} seasons there is no season left to test a forecast on. "
                f"Add at least {MIN_TRAIN + 1} consecutive seasons to evaluate the models."}
    points = next(iter(h1.values()))["n"]
    ranked = sorted(h1, key=lambda k: h1[k]["wape"])
    best = ranked[0]
    lin = h1["linear"]
    naive, drift = h1["naive"], h1["drift"]
    beats_naive = lin["mae"] < naive["mae"]
    beats_drift = lin["mae"] < drift["mae"]
    spread_pp = (h1[ranked[-1]]["wape"] - h1[best]["wape"]) * 100
    if points < RELIABLE_POINTS:
        level = "indicative"
        message = (f"Only {points} one-season-ahead test{'s' if points != 1 else ''} are possible with {n_seasons} seasons "
                   f"of history, so these errors are indicative, not proof of accuracy. A single unusual season "
                   f"could reorder the models. Treat the forecast range, not the point, as the planning figure.")
    else:
        level = "usable"
        message = f"{points} one-season-ahead tests support a meaningful comparison."
    return {
        "level": level, "points": points, "best": best, "best_label": LABELS[best],
        "linear_beats_naive": beats_naive, "linear_beats_drift": beats_drift,
        "wape_spread_pp": spread_pp, "message": message,
    }


def evaluate(series: list[dict], key: str = "production_t") -> dict:
    """Full evaluation of the forecast models on one metric of a season series."""
    seasons = [r["season"] for r in series]
    ys = [r[key] for r in series]
    rows = rolling_origin(seasons, ys)
    m = metrics(rows)
    return {
        "metric": key,
        "n_seasons": len(series),
        "min_train": MIN_TRAIN,
        "horizons": list(HORIZONS),
        "models": [{"key": k, "label": lab, "kind": kind} for k, lab, kind, _f in MODELS],
        "metrics": {k: {str(h): v for h, v in hs.items()} for k, hs in m.items()},
        "rows": rows,
        "assessment": assess(m, len(series)),
    }
