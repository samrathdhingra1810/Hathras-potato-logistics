// Production & yield analytics: growth rates, summary stats, OLS forecasting.

// Two-sided Student-t critical values at 95% for small samples (df -> t).
const T_95 = { 1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228 };

export function pctChange(current, previous) {
  if (!previous) return null;
  return (current - previous) / previous;
}

export function mean(values) {
  return values.reduce((s, v) => s + v, 0) / values.length;
}

/** Compound annual growth rate between the first and last value over `periods` steps. */
export function cagr(first, last, periods) {
  if (first <= 0 || periods <= 0) return null;
  return Math.pow(last / first, 1 / periods) - 1;
}

/** Appends YoY change for area, production and yield to each season row. */
export function withYoY(series) {
  return series.map((row, i) => {
    const prev = series[i - 1];
    return {
      ...row,
      yieldTHa: row.yieldKgHa / 1000,
      areaYoY: prev ? pctChange(row.areaHa, prev.areaHa) : null,
      productionYoY: prev ? pctChange(row.productionT, prev.productionT) : null,
      yieldYoY: prev ? pctChange(row.yieldKgHa, prev.yieldKgHa) : null,
    };
  });
}

/**
 * Ordinary least squares fit of y on x.
 * Returns slope, intercept, r2, residual standard error and a predict(x0) that
 * yields the point estimate plus a 95% prediction interval.
 */
export function linearRegression(xs, ys) {
  const n = xs.length;
  if (n < 3) throw new Error('linearRegression needs at least 3 points');
  const xBar = mean(xs);
  const yBar = mean(ys);
  let sxx = 0;
  let sxy = 0;
  let syy = 0;
  for (let i = 0; i < n; i++) {
    sxx += (xs[i] - xBar) ** 2;
    sxy += (xs[i] - xBar) * (ys[i] - yBar);
    syy += (ys[i] - yBar) ** 2;
  }
  const slope = sxy / sxx;
  const intercept = yBar - slope * xBar;
  const sse = xs.reduce((s, x, i) => s + (ys[i] - (intercept + slope * x)) ** 2, 0);
  const df = n - 2;
  const se = Math.sqrt(sse / df);
  const r2 = syy === 0 ? 1 : 1 - sse / syy;
  const t = T_95[df] ?? 1.96;

  const predict = (x0) => {
    const value = intercept + slope * x0;
    const margin = t * se * Math.sqrt(1 + 1 / n + (x0 - xBar) ** 2 / sxx);
    return { value, lower: value - margin, upper: value + margin };
  };

  return { slope, intercept, r2, se, n, predict };
}

/** "2023-24" -> "2024-25", stepping by `k` seasons. */
export function nextSeason(season, k = 1) {
  const start = Number(season.slice(0, 4)) + k;
  return `${start}-${String((start + 1) % 100).padStart(2, '0')}`;
}

/**
 * Forecasts area, production and yield for the next `horizon` seasons by fitting
 * an independent linear trend to each metric against the season index.
 */
export function forecastSeries(series, horizon = 2) {
  const xs = series.map((_, i) => i);
  const models = {
    areaHa: linearRegression(xs, series.map((r) => r.areaHa)),
    productionT: linearRegression(xs, series.map((r) => r.productionT)),
    yieldKgHa: linearRegression(xs, series.map((r) => r.yieldKgHa)),
  };
  const last = series[series.length - 1];
  const rows = [];
  for (let k = 1; k <= horizon; k++) {
    const x0 = series.length - 1 + k;
    const p = models.productionT.predict(x0);
    const y = models.yieldKgHa.predict(x0);
    const a = models.areaHa.predict(x0);
    rows.push({
      season: nextSeason(last.season, k),
      forecast: true,
      areaHa: a.value,
      productionT: p.value,
      productionLower: p.lower,
      productionUpper: p.upper,
      yieldKgHa: y.value,
      yieldLower: y.lower,
      yieldUpper: y.upper,
    });
  }
  return {
    rows,
    models: Object.fromEntries(
      Object.entries(models).map(([k, m]) => [k, { slope: m.slope, intercept: m.intercept, r2: m.r2, se: m.se, n: m.n }]),
    ),
  };
}

/** Rebases a metric to 100 at the first season so different units share one axis. */
export function indexTo100(series, key) {
  const base = series[0][key];
  return series.map((r) => (r[key] / base) * 100);
}
