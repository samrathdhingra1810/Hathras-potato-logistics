// Chart helpers on top of Chart.js 4. Colors come from CSS tokens, so charts
// rebuild on theme change. No dual axes: different units get separate charts
// or are indexed to a common base.
(function () {
  var HP = (window.HP = window.HP || {});
  var registry = [];

  HP.pageData = function () {
    var el = document.getElementById('page-data');
    return el ? JSON.parse(el.textContent) : {};
  };

  /** 'var(--series-1)' or '--series-1' -> resolved color string. */
  HP.color = function (v) {
    var m = /^var\((--[^)]+)\)$/.exec(v) || /^(--.+)$/.exec(v);
    if (!m) return v;
    return getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim();
  };

  var nf0 = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
  HP.fmt = {
    num: function (v) { return v == null ? '—' : nf0.format(v); },
    tFull: function (v) { return v == null ? '—' : nf0.format(v) + ' t'; },
    t: function (v) {
      if (v == null || !isFinite(v)) return '—';
      var a = Math.abs(v);
      if (a >= 1e6) return (v / 1e6).toFixed(2) + 'M t';
      if (a >= 1e3) return (v / 1e3).toFixed(a >= 1e5 ? 0 : 1) + 'k t';
      return Math.round(v) + ' t';
    },
    axisT: function (v) {
      var a = Math.abs(v);
      if (a >= 1e6) return (v / 1e6).toFixed(2) + 'M';
      if (a >= 1e3) return Math.round(v / 1e3) + 'k';
      return String(Math.round(v));
    },
    ha: function (v) { return nf0.format(v) + ' ha'; },
    kgha: function (v) { return nf0.format(v) + ' kg/ha'; },
    pct: function (v, d, signed) {
      if (v == null || !isFinite(v)) return '—';
      var s = (v * 100).toFixed(d == null ? 1 : d) + '%';
      return signed && v > 0 ? '+' + s : s;
    },
  };

  function base() {
    var muted = HP.color('--ink-muted');
    var line = HP.color('--line');
    var axis = HP.color('--axis');
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      animation: { duration: 500 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: HP.color('--surface'),
          titleColor: HP.color('--ink'),
          bodyColor: HP.color('--ink-2'),
          footerColor: HP.color('--ink-2'),
          borderColor: line,
          borderWidth: 1,
          padding: 10,
          boxPadding: 4,
          usePointStyle: true,
          titleFont: { weight: '600' },
        },
      },
      scales: {
        x: { grid: { display: false }, border: { color: axis }, ticks: { color: muted, font: { size: 11 } } },
        y: { grid: { color: line }, border: { display: false }, ticks: { color: muted, font: { size: 11 } } },
      },
    };
  }

  function lineDs(label, data, color, extra) {
    var c = HP.color(color);
    return Object.assign({
      label: label, data: data, borderColor: c, backgroundColor: c, borderWidth: 2, tension: 0,
      pointRadius: 4, pointHoverRadius: 5, pointBackgroundColor: c,
      pointBorderColor: HP.color('--surface'), pointBorderWidth: 2,
    }, extra || {});
  }

  /** Draws a text label next to the last point of the given datasets. */
  var endLabels = {
    id: 'endLabels',
    afterDatasetsDraw: function (chart, _args, opts) {
      if (!opts || !opts.labels) return;
      var ctx = chart.ctx;
      ctx.save();
      ctx.font = '600 11px system-ui, -apple-system, sans-serif';
      ctx.fillStyle = HP.color('--ink-2');
      ctx.textBaseline = 'middle';
      opts.labels.forEach(function (l) {
        var meta = chart.getDatasetMeta(l.dataset);
        var pt = meta.data[meta.data.length - 1];
        if (pt) ctx.fillText(l.text, pt.x + 9, pt.y);
      });
      ctx.restore();
    },
  };

  /** Shades a category range (e.g. Feb–Apr) behind the bars. */
  var shadeRange = {
    id: 'shadeRange',
    beforeDatasetsDraw: function (chart, _args, opts) {
      if (!opts || opts.from == null) return;
      var x = chart.scales.x, area = chart.chartArea, ctx = chart.ctx;
      var step = x.getPixelForValue(1) - x.getPixelForValue(0);
      var left = x.getPixelForValue(opts.from) - step / 2;
      var right = x.getPixelForValue(opts.to) + step / 2;
      ctx.save();
      ctx.fillStyle = HP.color('--surface-2');
      ctx.fillRect(left, area.top, right - left, area.bottom - area.top);
      ctx.fillStyle = HP.color('--ink-muted');
      ctx.font = '600 10px system-ui, -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(opts.label || '', (left + right) / 2, area.top + 12);
      ctx.restore();
    },
  };

  /** Creates a chart on canvas #id from configFn(); rebuilt on theme change. */
  HP.chart = function (id, configFn) {
    var canvas = document.getElementById(id);
    if (!canvas || !window.Chart) return { rebuild: function () {}, update: function () {} };
    var entry = { canvas: canvas, configFn: configFn, chart: null };
    entry.rebuild = function () {
      if (entry.chart) entry.chart.destroy();
      var cfg = configFn();
      cfg.plugins = (cfg.plugins || []).concat([endLabels, shadeRange]);
      entry.chart = new Chart(canvas, cfg);
    };
    entry.rebuild();
    registry.push(entry);
    return entry;
  };
  HP.resizeAll = function () { registry.forEach(function (e) { if (e.chart) e.chart.resize(); }); };
  document.addEventListener('themechange', function () { registry.forEach(function (e) { e.rebuild(); }); });

  /** Wires a .seg[data-seg=name] radiogroup; cb(value) on change. */
  HP.segmented = function (name, cb) {
    var group = document.querySelector('[data-seg="' + name + '"]');
    if (!group) return;
    group.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-value]');
      if (!btn) return;
      group.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-checked', String(b === btn)); });
      cb(btn.dataset.value);
    });
  };

  // ---------- Chart configs ----------

  HP.indexedConfig = function (series) {
    var a0 = series[0].area_ha, p0 = series[0].production_t;
    var area = series.map(function (r) { return (r.area_ha / a0) * 100; });
    var prod = series.map(function (r) { return (r.production_t / p0) * 100; });
    var o = base();
    o.layout = { padding: { right: 86 } };
    o.scales.y.ticks.callback = function (v) { return v.toFixed(0); };
    o.plugins.endLabels = { labels: [
      { dataset: 0, text: 'Area ' + area[area.length - 1].toFixed(1) },
      { dataset: 1, text: 'Output ' + prod[prod.length - 1].toFixed(1) },
    ] };
    o.plugins.tooltip.callbacks = {
      label: function (ctx) {
        var r = series[ctx.dataIndex];
        return ctx.datasetIndex === 0
          ? ' Area ' + HP.fmt.ha(r.area_ha) + ' (index ' + ctx.parsed.y.toFixed(1) + ')'
          : ' Output ' + HP.fmt.tFull(r.production_t) + ' (index ' + ctx.parsed.y.toFixed(1) + ')';
      },
    };
    return {
      type: 'line',
      data: { labels: series.map(function (r) { return r.season; }), datasets: [
        lineDs('Area cultivated', area, '--series-1'),
        lineDs('Harvest output', prod, '--series-2'),
      ] },
      options: o,
    };
  };

  HP.singleConfig = function (series, key, color, label, fmt, average) {
    var yoyKey = { area_ha: 'area_yoy', production_t: 'production_yoy', yield_kg_ha: 'yield_yoy' }[key];
    var datasets = [lineDs(label, series.map(function (r) { return r[key]; }), color)];
    if (average != null) {
      datasets.push(lineDs('Six-season average', series.map(function () { return average; }), '--ink-muted',
        { borderDash: [5, 4], borderWidth: 1.5, pointRadius: 0, pointHoverRadius: 0 }));
    }
    var o = base();
    o.scales.y.ticks.callback = key === 'production_t' ? HP.fmt.axisT : function (v) { return HP.fmt.num(v); };
    o.plugins.tooltip.callbacks = {
      label: function (ctx) {
        if (ctx.datasetIndex === 1) return ' Average ' + fmt(ctx.parsed.y);
        return ' ' + label + ' ' + fmt(ctx.parsed.y) + '  (YoY ' + HP.fmt.pct(series[ctx.dataIndex][yoyKey], 2, true) + ')';
      },
    };
    return { type: 'line', data: { labels: series.map(function (r) { return r.season; }), datasets: datasets }, options: o };
  };

  /** metric: 'production' | 'yield'. Actual solid, forecast dashed, 95% band. */
  HP.forecastConfig = function (series, rows, metric, opts) {
    opts = opts || {};
    var key = metric === 'yield' ? 'yield_kg_ha' : 'production_t';
    var lo = metric === 'yield' ? 'yield_lower' : 'production_lower';
    var hi = metric === 'yield' ? 'yield_upper' : 'production_upper';
    var fmt = metric === 'yield' ? HP.fmt.kgha : HP.fmt.tFull;
    var n = series.length;
    var labels = series.map(function (r) { return r.season; }).concat(rows.map(function (r) { return r.season; }));
    var actual = series.map(function (r) { return r[key]; }).concat(rows.map(function () { return null; }));
    var proj = series.map(function (r, i) { return i === n - 1 ? r[key] : null; }).concat(rows.map(function (r) { return r[key]; }));
    var lower = series.map(function (r, i) { return i === n - 1 ? r[key] : null; }).concat(rows.map(function (r) { return r[lo]; }));
    var upper = series.map(function (r, i) { return i === n - 1 ? r[key] : null; }).concat(rows.map(function (r) { return r[hi]; }));
    var band = HP.color('--band-1');
    var c = HP.color('--series-1');

    var o = base();
    o.scales.y.ticks.callback = metric === 'yield' ? function (v) { return HP.fmt.num(v); } : HP.fmt.axisT;
    if (opts.compact) { o.scales.y.ticks.maxTicksLimit = 4; o.scales.x.ticks.maxRotation = 0; o.scales.x.ticks.autoSkip = true; }
    o.plugins.tooltip.filter = function (item) { return item.datasetIndex >= 2 && item.raw != null; };
    o.plugins.tooltip.callbacks = {
      title: function (items) { var i = items[0].dataIndex; return labels[i] + (i >= n ? ' (forecast)' : ''); },
      label: function (ctx) {
        var i = ctx.dataIndex;
        if (ctx.datasetIndex === 2) return ' Actual ' + fmt(ctx.parsed.y);
        if (i < n) return null;
        return ' Projected ' + fmt(ctx.parsed.y);
      },
      footer: function (items) {
        var i = items[0].dataIndex;
        return i >= n ? '95% range ' + fmt(lower[i]) + ' – ' + fmt(upper[i]) : '';
      },
    };
    return {
      type: 'line',
      data: { labels: labels, datasets: [
        { label: 'lower', data: lower, borderWidth: 0, pointRadius: 0, pointHoverRadius: 0, fill: false },
        { label: 'upper', data: upper, borderWidth: 0, pointRadius: 0, pointHoverRadius: 0, fill: '-1', backgroundColor: band },
        lineDs('Actual', actual, '--series-1'),
        lineDs('Forecast', proj, '--series-1', { borderDash: [6, 4], pointBackgroundColor: HP.color('--surface'), pointBorderColor: c }),
      ] },
      options: o,
    };
  };

  /** Monthly stock (blue) + unmet demand (critical) stacked; capacity & threshold lines. */
  HP.storageConfig = function (scenario) {
    var sim = scenario.simulation;
    var cap = scenario.inputs.capacity;
    var thr = scenario.inputs.threshold;
    var months = sim.months.map(function (m) { return m.month; });
    var o = base();
    o.scales.x.stacked = true;
    o.scales.y.stacked = true;
    o.scales.y.beginAtZero = true;
    o.scales.y.suggestedMax = Math.max(cap, sim.months.reduce(function (a, m) { return Math.max(a, m.demanded_stock); }, 0)) * 1.12;
    o.scales.y.ticks.callback = HP.fmt.axisT;
    o.plugins.shadeRange = { from: 1, to: 3, label: 'Peak harvest' };
    o.plugins.tooltip.filter = function (item) { return item.datasetIndex < 2; };
    o.plugins.tooltip.callbacks = {
      label: function (ctx) {
        if (ctx.datasetIndex === 1 && !ctx.parsed.y) return null;
        return ' ' + ctx.dataset.label + ' ' + HP.fmt.t(ctx.parsed.y);
      },
      footer: function (items) {
        var m = sim.months[items[0].dataIndex];
        return ['Intake ' + HP.fmt.t(m.intake) + ' · Release ' + HP.fmt.t(m.release),
                'Utilisation ' + HP.fmt.pct(m.utilisation, 1)];
      },
    };
    var surface = HP.color('--surface');
    return {
      type: 'bar',
      data: { labels: months, datasets: [
        { type: 'bar', label: 'Stock held', data: sim.months.map(function (m) { return m.stock; }), backgroundColor: HP.color('--series-1'),
          borderColor: surface, borderWidth: { top: 2 }, borderSkipped: false, stack: 's', categoryPercentage: 0.72, barPercentage: 0.9 },
        { type: 'bar', label: 'Unmet demand', data: sim.months.map(function (m) { return m.unmet; }), backgroundColor: HP.color('--status-critical'),
          borderRadius: { topLeft: 4, topRight: 4 }, borderSkipped: false, stack: 's', categoryPercentage: 0.72, barPercentage: 0.9 },
        { type: 'line', label: 'Capacity', data: months.map(function () { return cap; }), borderColor: HP.color('--ink'),
          borderWidth: 1.5, pointRadius: 0, pointHoverRadius: 0, stack: 'cap' },
        { type: 'line', label: 'Alert threshold', data: months.map(function () { return cap * thr; }), borderColor: HP.color('--status-serious'),
          borderWidth: 1.5, borderDash: [5, 4], pointRadius: 0, pointHoverRadius: 0, stack: 'thr' },
      ] },
      options: o,
    };
  };
})();
