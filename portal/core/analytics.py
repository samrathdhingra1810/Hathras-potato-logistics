"""Production & yield analytics: growth rates, summary stats, OLS forecasting."""
from __future__ import annotations

import math
from datetime import date

# Two-sided Student-t critical values at 95% for small samples (df -> t).
_T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}


def pct_change(current: float, previous: float) -> float | None:
    if not previous:
        return None
    return (current - previous) / previous


def mean(values) -> float:
    values = list(values)
    return sum(values) / len(values)


def cagr(first: float, last: float, periods: int) -> float | None:
    if first <= 0 or periods <= 0:
        return None
    return (last / first) ** (1 / periods) - 1


def with_yoy(series: list[dict]) -> list[dict]:
    """Copies each season row and adds YoY change for area, production and yield."""
    out = []
    for i, row in enumerate(series):
        prev = series[i - 1] if i else None
        out.append({
            **row,
            "yield_t_ha": row["yield_kg_ha"] / 1000,
            "area_yoy": pct_change(row["area_ha"], prev["area_ha"]) if prev else None,
            "production_yoy": pct_change(row["production_t"], prev["production_t"]) if prev else None,
            "yield_yoy": pct_change(row["yield_kg_ha"], prev["yield_kg_ha"]) if prev else None,
        })
    return out


class LinearModel:
    """Ordinary least squares fit of y on x with a 95% prediction interval."""

    def __init__(self, xs, ys):
        n = len(xs)
        if n < 3:
            raise ValueError("LinearModel needs at least 3 points")
        x_bar, y_bar = mean(xs), mean(ys)
        sxx = sum((x - x_bar) ** 2 for x in xs)
        sxy = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys))
        syy = sum((y - y_bar) ** 2 for y in ys)
        self.n = n
        self.slope = sxy / sxx
        self.intercept = y_bar - self.slope * x_bar
        sse = sum((y - (self.intercept + self.slope * x)) ** 2 for x, y in zip(xs, ys))
        df = n - 2
        self.se = math.sqrt(sse / df)
        self.r2 = 1.0 if syy == 0 else 1 - sse / syy
        self._t = _T95.get(df, 1.96)
        self._x_bar, self._sxx = x_bar, sxx

    def predict(self, x0: float) -> dict:
        value = self.intercept + self.slope * x0
        margin = self._t * self.se * math.sqrt(1 + 1 / self.n + (x0 - self._x_bar) ** 2 / self._sxx)
        return {"value": value, "lower": value - margin, "upper": value + margin}

    def summary(self) -> dict:
        return {"slope": self.slope, "intercept": self.intercept, "r2": self.r2, "se": self.se, "n": self.n}


def next_season(season: str, k: int = 1) -> str:
    """'2023-24' -> '2024-25', stepping by k seasons."""
    start = int(season[:4]) + k
    return f"{start}-{(start + 1) % 100:02d}"


def forecast_seasons(series: list[dict], horizon: int = 2) -> list[str]:
    """Labels of the seasons the forecasts cover: the `horizon` seasons after the latest record."""
    return [next_season(series[-1]["season"], k) for k in range(1, horizon + 1)]


def harvested_seasons(seasons: list[str], today) -> list[str]:
    """Seasons whose harvest is already over on `today`.

    A season 'YYYY-YY' is dug Feb–Mar of its second year and loaded into cold
    storage by April (dataset.MONTHLY_INTAKE_PROFILE), so it counts as harvested
    from 1 May of that year. Used only to label forecasts; it adds no data.
    """
    return [s for s in seasons if (today.year, today.month) >= (int(s[:4]) + 1, 5)]


ESTIMATE_LABEL = "Estimate · past season, pending verified actuals"
FORECAST_LABEL = "Forecast"


def season_status(season: str, today: date | None = None) -> dict:
    """How to label a modelled (non-actual) season. Labels only; the numbers are untouched.

    'estimate' = the season's harvest is already over but no verified actual is in the
    series, so the model value stands in for it. 'forecast' = the harvest is still ahead.
    """
    past = bool(harvested_seasons([season], today or date.today()))
    return {"status": "estimate" if past else "forecast", "status_label": ESTIMATE_LABEL if past else FORECAST_LABEL}


def forecast_series(series: list[dict], horizon: int = 2) -> dict:
    """Independent linear trend per metric against the season index."""
    xs = list(range(len(series)))
    models = {key: LinearModel(xs, [r[key] for r in series]) for key in ("area_ha", "production_t", "yield_kg_ha")}
    last = series[-1]
    rows = []
    for k in range(1, horizon + 1):
        x0 = len(series) - 1 + k
        a = models["area_ha"].predict(x0)
        p = models["production_t"].predict(x0)
        y = models["yield_kg_ha"].predict(x0)
        rows.append({
            "season": next_season(last["season"], k),
            "forecast": True,
            **season_status(next_season(last["season"], k)),
            "area_ha": a["value"],
            "production_t": p["value"],
            "production_lower": p["lower"],
            "production_upper": p["upper"],
            "yield_kg_ha": y["value"],
            "yield_lower": y["lower"],
            "yield_upper": y["upper"],
        })
    return {"rows": rows, "models": {k: m.summary() for k, m in models.items()}}


def summary(series: list[dict]) -> dict:
    """Headline numbers used across the site."""
    s = with_yoy(series)
    latest, prev = s[-1], s[-2]
    return {
        "latest": latest,
        "previous": prev,
        "first": s[0],
        "cagr": cagr(s[0]["production_t"], latest["production_t"], len(s) - 1),
        "avg_yield_kg_ha": mean(r["yield_kg_ha"] for r in s),
        "area_growth": pct_change(latest["area_ha"], s[0]["area_ha"]),
        "yield_growth": pct_change(latest["yield_kg_ha"], s[0]["yield_kg_ha"]),
    }


# ---------------------------------------------------------------- exponential smoothing

def _holt_fit(ys, alpha, beta, phi):
    """Damped-trend Holt smoothing. Returns (level, trend, one-step-ahead residuals).

    The state is initialised from the first two points (level = y1, trend = y1 − y0),
    so residuals start at the third point; scoring y1 would reuse it in its own
    initial trend and flatter the fit.
    """
    level, trend = ys[1], ys[1] - ys[0]
    resid = []
    for y in ys[2:]:
        pred = level + phi * trend
        resid.append(y - pred)
        new_level = alpha * y + (1 - alpha) * pred
        trend = beta * (new_level - level) + (1 - beta) * phi * trend
        level = new_level
    return level, trend, resid


def holt_damped(ys, horizon=2):
    """Grid-searched damped Holt model; small-sample friendly. Intervals are approximate."""
    if len(ys) < 3:
        raise ValueError("holt_damped needs at least 3 points")
    grid = [i / 10 for i in range(1, 10)]
    best = None
    for alpha in grid:
        for beta in grid:
            for phi in (0.8, 0.9, 0.98):
                level, trend, resid = _holt_fit(ys, alpha, beta, phi)
                sse = sum(r * r for r in resid)
                if best is None or sse < best[0]:
                    best = (sse, alpha, beta, phi, level, trend, resid)
    sse, alpha, beta, phi, level, trend, resid = best
    sd = math.sqrt(sse / max(len(resid) - 1, 1))
    out = []
    damp = 0.0
    for h in range(1, horizon + 1):
        damp += phi ** h
        value = level + damp * trend
        # Approximate 95% band widening with horizon (standard ETS(A,Ad,N) form, simplified).
        margin = 1.96 * sd * math.sqrt(1 + (h - 1) * alpha ** 2 * (1 + beta) ** 2)
        out.append({"value": value, "lower": value - margin, "upper": value + margin})
    return {"params": {"alpha": alpha, "beta": beta, "phi": phi}, "sd": sd, "rows": out}


def forecast_smoothing(series: list[dict], horizon: int = 2) -> dict:
    """Same row shape as forecast_series(), using damped exponential smoothing per metric."""
    fits = {k: holt_damped([r[k] for r in series], horizon) for k in ("area_ha", "production_t", "yield_kg_ha")}
    last = series[-1]
    rows = []
    for k in range(horizon):
        a, p, y = fits["area_ha"]["rows"][k], fits["production_t"]["rows"][k], fits["yield_kg_ha"]["rows"][k]
        rows.append({
            "season": next_season(last["season"], k + 1), "forecast": True,
            **season_status(next_season(last["season"], k + 1)),
            "area_ha": a["value"], "production_t": p["value"],
            "production_lower": p["lower"], "production_upper": p["upper"],
            "yield_kg_ha": y["value"], "yield_lower": y["lower"], "yield_upper": y["upper"],
        })
    return {"rows": rows, "params": {k: v["params"] for k, v in fits.items()}}


def compare_models(series: list[dict], horizon: int = 2) -> dict:
    """Both forecasts plus a rolling-origin evaluation against simple baselines.

    The linear trend stays the primary (headline) model: with only a handful of
    evaluation points, the evidence is not strong enough to switch models
    automatically. The evaluation is reported alongside so users can judge.
    """
    from .evaluation import evaluate  # local import: evaluation imports this module

    return {
        "linear": forecast_series(series, horizon),
        "smoothing": forecast_smoothing(series, horizon),
        "evaluation": evaluate(series, "production_t"),
        "primary": "linear",
    }
