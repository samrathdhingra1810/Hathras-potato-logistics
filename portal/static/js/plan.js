// Own-data planner: editable seasons + settings -> /api/analyse (Python engine) -> results.
// State lives in the page and in the URL hash (#d=...), so a plan can be shared as a link.
(function () {
  var d = HP.pageData();
  var fmt = HP.fmt;
  var WHATIF = ['yield_shock', 'extra_capacity', 'tariff_change', 'tariff', 'kwh'];
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var ICONS = { good: '●', warning: '▲', serious: '◆', critical: '■' };
  var $ = function (id) { return document.getElementById(id); };

  var planId = d.saved ? d.saved.id : null;
  var analysis = null;
  var fcMetric = 'production';
  var chosenSeason = '';

  // ---------- State <-> form ----------
  function rowHtml(r) {
    var v = function (x) { return x == null || x === '' ? '' : x; };
    return '<tr>' +
      '<td><input name="season" aria-label="Season" placeholder="2023-24" value="' + v(r.season) + '"></td>' +
      '<td><input name="area_ha" aria-label="Area in hectares" type="number" min="0" step="any" inputmode="decimal" value="' + v(r.area_ha) + '"></td>' +
      '<td><input name="production_t" aria-label="Production in tonnes" type="number" min="0" step="any" inputmode="decimal" value="' + v(r.production_t) + '"></td>' +
      '<td class="r muted" data-yield></td>' +
      '<td><button type="button" class="row-x" aria-label="Remove season" data-remove>×</button></td></tr>';
  }

  function setState(s) {
    $('plan-name').value = s.name || '';
    $('rows').innerHTML = (s.series || []).map(rowHtml).join('');
    $('capacity').value = Math.round(s.capacity);
    $('ratio').value = s.ratio;
    $('threshold').value = s.threshold;
    $('facility').value = Math.round(s.facility);
    WHATIF.forEach(function (k) { if (s[k] != null) $(k).value = s[k]; else if (d.example[k] != null) $(k).value = d.example[k]; });
    setCalendar('intake', s.intake_profile);
    setCalendar('release', s.release_profile);
    chosenSeason = s.season || '';
    updateYields();
    showOutputs();
  }

  function setCalendar(kind, profile) {
    var total = MONTHS.reduce(function (a, m) { return a + (+profile[m] || 0); }, 0);
    var scale = total > 1.5 ? 1 : 100; // stored as fractions; shown as %
    document.querySelectorAll('[data-cal="' + kind + '"]').forEach(function (el) {
      var v = +profile[el.dataset.month] || 0;
      el.value = v ? +(v * scale).toFixed(1) : '';
    });
    calSum(kind);
  }

  function readCalendar(kind) {
    var out = {};
    document.querySelectorAll('[data-cal="' + kind + '"]').forEach(function (el) {
      var v = parseFloat(el.value);
      if (v > 0) out[el.dataset.month] = v / 100;
    });
    return out;
  }

  function calSum(kind) {
    var total = 0;
    document.querySelectorAll('[data-cal="' + kind + '"]').forEach(function (el) { total += parseFloat(el.value) || 0; });
    var el = document.querySelector('[data-sum="' + kind + '"]');
    el.textContent = 'Total ' + total.toFixed(0) + '%' + (Math.abs(total - 100) > 0.5 ? ' (will be scaled to 100%)' : '');
  }

  function readState() {
    var series = [];
    $('rows').querySelectorAll('tr').forEach(function (tr) {
      var get = function (n) { return tr.querySelector('[name="' + n + '"]').value.trim(); };
      var row = { season: get('season'), area_ha: get('area_ha'), production_t: get('production_t') };
      if (row.season || row.area_ha || row.production_t) {
        series.push({ season: row.season, area_ha: row.area_ha === '' ? null : +row.area_ha,
                      production_t: row.production_t === '' ? null : +row.production_t });
      }
    });
    return {
      name: $('plan-name').value.trim() || 'My district',
      series: series,
      capacity: +$('capacity').value,
      ratio: +$('ratio').value,
      threshold: +$('threshold').value,
      facility: +$('facility').value,
      intake_profile: readCalendar('intake'),
      release_profile: readCalendar('release'),
      season: chosenSeason,
      yield_shock: +$('yield_shock').value,
      extra_capacity: +$('extra_capacity').value,
      tariff_change: +$('tariff_change').value,
      tariff: +$('tariff').value,
      kwh: +$('kwh').value,
    };
  }

  function updateYields() {
    $('rows').querySelectorAll('tr').forEach(function (tr) {
      var a = parseFloat(tr.querySelector('[name="area_ha"]').value);
      var p = parseFloat(tr.querySelector('[name="production_t"]').value);
      tr.querySelector('[data-yield]').textContent = a > 0 && p > 0 ? (p / a).toFixed(1) + ' t/ha' : '—';
    });
  }

  function showOutputs() {
    document.querySelector('[data-out="ratio"]').textContent = fmt.pct(+$('ratio').value, 0);
    document.querySelector('[data-out="threshold"]').textContent = fmt.pct(+$('threshold').value, 0);
    HP.whatifOutputs();
  }

  // ---------- URL hash (shareable state) ----------
  function encode(s) {
    var json = JSON.stringify(s);
    return btoa(unescape(encodeURIComponent(json))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function decode(str) {
    try {
      var b = str.replace(/-/g, '+').replace(/_/g, '/');
      return JSON.parse(decodeURIComponent(escape(atob(b))));
    } catch (e) { return null; }
  }
  function writeHash(s) {
    if (planId) return; // saved plans are addressed by ?plan=id instead
    history.replaceState(null, '', location.pathname + location.search + '#d=' + encode(s));
  }

  // ---------- Results ----------
  function bind(name, text) {
    document.querySelectorAll('[data-bind="' + name + '"]').forEach(function (el) { el.textContent = text; });
  }

  function alertText(a) {
    var sim = a.simulation, i = a.inputs;
    switch (sim.status) {
      case 'critical':
        return ['Storage deficit in ' + sim.deficit_months.join(', ') + ' (' + i.season + ')',
          'Intake exceeds capacity by ' + fmt.t(sim.total_overflow_t) + '. That volume has no cold-chain slot.'];
      case 'serious':
        return ['Capacity strained in ' + sim.alert_months.join(', ') + ' (' + i.season + ')',
          'Peak stock reaches ' + fmt.pct(sim.peak_utilisation) + ' of capacity, above your ' + fmt.pct(i.threshold, 0) + ' threshold.'];
      case 'warning':
        return ['Approaching your threshold (' + i.season + ')',
          'Peak utilisation ' + fmt.pct(sim.peak_utilisation) + ' in ' + sim.peak_month + '.'];
      default:
        return ['Capacity adequate (' + i.season + ')',
          'Peak utilisation ' + fmt.pct(sim.peak_utilisation) + ' in ' + sim.peak_month + ', with ' + fmt.t(i.capacity - a.demand_t) + ' of headroom.'];
    }
  }

  var storageChart = HP.chart('storage-chart', function () {
    return analysis ? HP.storageConfig(analysis) : { type: 'bar', data: { labels: [], datasets: [] } };
  });
  var forecastChart = HP.chart('forecast-chart', function () {
    return analysis ? HP.forecastConfig(analysis.series, fcRows(), fcMetric) : { type: 'line', data: { labels: [], datasets: [] } };
  });
  HP.segmented('fc', function (v) { fcMetric = v; forecastChart.rebuild(); });
  var fcModel = 'linear';
  function fcRows() { return fcModel === 'smoothing' ? analysis.forecast_compare.smoothing.rows : analysis.forecast.rows; }
  HP.segmented('model', function (v) {
    fcModel = v;
    bind('fc-desc', v === 'smoothing' ? 'Damped exponential smoothing on your seasons, approximate 95% interval' : 'Linear trend on your seasons, 95% prediction interval');
    forecastChart.rebuild();
    renderFcTable();
  });

  function render(a) {
    analysis = a;
    $('errors').hidden = true;
    $('results').style.opacity = '';
    var w = a.warnings || [];
    $('warnings').hidden = !w.length;
    $('warn-list').innerHTML = w.map(function (x) { return '<li>' + escapeHtml(x) + '</li>'; }).join('');

    var s = a.series, last = s[s.length - 1];
    bind('name', a.name);
    bind('latest', fmt.t(last.production_t));
    bind('latest-season', last.season);
    bind('yoy', fmt.pct(last.production_yoy, 2, true));
    bind('cagr', fmt.pct(a.summary.cagr, 2));
    bind('cagr-span', 'per year since ' + s[0].season);
    bind('yield', (a.summary.avg_yield_kg_ha / 1000).toFixed(2) + ' t/ha');

    var sel = $('season');
    sel.innerHTML = a.seasons.map(function (o) {
      return '<option value="' + o.value + '"' + (o.value === a.inputs.season ? ' selected' : '') + '>Outlook: ' + o.label + '</option>';
    }).join('');

    var sim = a.simulation;
    var al = $('alert');
    al.className = 'alert lvl-' + sim.status;
    al.setAttribute('role', sim.status === 'critical' || sim.status === 'serious' ? 'alert' : 'status');
    var t = alertText(a);
    bind('alert-icon', ICONS[sim.status]);
    bind('alert-title', t[0]);
    bind('alert-body', t[1]);
    bind('production', fmt.t(a.production_t));
    bind('season-label', a.inputs.season);
    bind('demand', fmt.t(a.demand_t));
    bind('ratio-label', fmt.pct(a.inputs.ratio, 0) + ' of harvest');
    bind('coverage', fmt.pct(a.district_coverage, 1));
    bind('gap', a.facilities_to_close_gap > 0
      ? 'gap ≈ ' + fmt.num(Math.ceil(a.facilities_to_close_gap)) + ' facilities of that size' : 'demand fully covered');
    bind('facility-cov', fmt.pct(a.facility_coverage, 2));
    bind('need', fmt.t(sim.capacity_needed_t));
    HP.renderEconomics(a, bind);
    bind('need-thr', fmt.t(sim.capacity_needed_threshold_t));

    renderFcTable();
    var bt = a.forecast_compare.backtest;
    bind('fc-backtest', bt.holdout ? 'Backtest on ' + bt.seasons.join(' and ') + ': linear ' + fmt.pct(bt.linear_mape, 1) + ' vs smoothing ' +
      fmt.pct(bt.smoothing_mape, 1) + ' average error. ' + (a.forecast_compare.recommended === 'smoothing' ? 'Smoothing' : 'Linear') + ' fitted your history better.'
      : 'Add at least 5 seasons to compare models on your own history.');

    storageChart.rebuild();
    forecastChart.rebuild();
  }

  function renderFcTable() {
    if (!analysis) return;
    $('fc-rows').innerHTML = fcRows().map(function (r) {
      return '<tr><td><strong>' + r.season + '</strong></td><td class="r">' + fmt.tFull(r.production_t) + '</td><td class="r muted">' +
        fmt.t(r.production_lower) + ' – ' + fmt.t(r.production_upper) + '</td><td class="r">' + fmt.kgha(r.yield_kg_ha) + '</td></tr>';
    }).join('');
  }

  function showErrors(list) {
    $('errors').hidden = false;
    $('errors').innerHTML = '<strong>Fix these to see results</strong><ul class="warn-list">' +
      list.map(function (x) { return '<li>' + escapeHtml(x) + '</li>'; }).join('') + '</ul>';
    $('results').style.opacity = '0.35';
    $('warnings').hidden = true;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; });
  }

  var timer = null, seq = 0, loaded = false;
  function refresh() {
    updateYields();
    showOutputs();
    clearTimeout(timer);
    timer = setTimeout(function () {
      var s = readState();
      var mine = ++seq;
      fetch('/api/analyse', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(s) })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
        .then(function (res) {
          if (mine !== seq) return;
          if (res.ok) { render(res.body); writeHash(s); if (loaded) markDirty(); loaded = true; }
          else showErrors(res.body.errors || [res.body.error || 'Something went wrong.']);
        })
        .catch(function () { if (mine === seq) showErrors(['Could not reach ColdFlow. Check your connection and try again.']); });
    }, 200);
  }

  // ---------- CSV ----------
  function toCsv(s) {
    return 'season,area_ha,production_t\n' + s.series.map(function (r) {
      return [r.season, r.area_ha == null ? '' : r.area_ha, r.production_t == null ? '' : r.production_t].join(',');
    }).join('\n') + '\n';
  }

  // ---------- Save ----------
  var dirty = false;
  function markDirty() {
    if (!d.canSave) return;
    if (dirty) return;
    dirty = true;
    if (planId) $('save-status').textContent = 'Unsaved changes';
  }
  function save() {
    var s = readState();
    var btn = $('save');
    btn.disabled = true;
    $('save-status').textContent = 'Saving…';
    fetch(planId ? '/api/plans/' + planId : '/api/plans', {
      method: planId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': d.csrf },
      body: JSON.stringify({ name: s.name, payload: s }),
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, body: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        if (!res.ok) {
          $('save-status').textContent = (res.body.errors && res.body.errors[0]) || res.body.error || 'Could not save.';
          return;
        }
        planId = res.body.id;
        dirty = false;
        history.replaceState(null, '', location.pathname + '?plan=' + planId);
        $('save-status').textContent = 'Saved ' + res.body.updated_at.slice(0, 16).replace('T', ' ') + ' UTC';
      })
      .catch(function () { btn.disabled = false; $('save-status').textContent = 'Could not save. Check your connection.'; });
  }

  // ---------- Wiring ----------
  document.querySelector('.split').addEventListener('input', function (e) {
    if (e.target.dataset.cal) calSum(e.target.dataset.cal);
    if (e.target.id === 'season') chosenSeason = e.target.value;
    refresh();
  });
  $('season').addEventListener('change', function (e) { chosenSeason = e.target.value; refresh(); });
  $('plan-name').addEventListener('input', refresh);
  $('rows').addEventListener('click', function (e) {
    if (e.target.closest('[data-remove]')) { e.target.closest('tr').remove(); refresh(); }
  });
  $('add-row').addEventListener('click', function () {
    var seasons = readState().series.map(function (r) { return r.season; }).filter(function (x) { return /^\d{4}-\d{2}$/.test(x); }).sort();
    var next = '';
    if (seasons.length) {
      var y = +seasons[seasons.length - 1].slice(0, 4) + 1;
      next = y + '-' + String((y + 1) % 100).padStart(2, '0');
    }
    $('rows').insertAdjacentHTML('beforeend', rowHtml({ season: next }));
    $('rows').lastElementChild.querySelector('[name="area_ha"]').focus();
  });
  $('clear-rows').addEventListener('click', function () {
    if (!confirm('Clear all seasons?')) return;
    $('rows').innerHTML = [0, 1, 2].map(function () { return rowHtml({}); }).join('');
    refresh();
  });
  $('load-example').addEventListener('click', function () { setState(d.example); refresh(); });
  $('district').addEventListener('change', function (e) {
    var id = e.target.value;
    if (!id) return;
    fetch('/api/districts/' + encodeURIComponent(id))
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        if (!res.ok) { showErrors([res.body.error]); return; }
        var st = readState();
        st.name = res.body.name; st.series = res.body.series; st.capacity = res.body.capacity;
        setState(st); refresh();
      });
  });
  $('cal-default').addEventListener('click', function () {
    setCalendar('intake', d.example.intake_profile);
    setCalendar('release', d.example.release_profile);
    refresh();
  });
  $('csv-file').addEventListener('change', function (e) {
    var f = e.target.files[0];
    e.target.value = '';
    if (!f) return;
    if (f.size > 400 * 1024) { showErrors(['That file is too large. Use a file under 400 KB.']); return; }
    var body = new FormData();
    body.append('file', f);
    fetch('/api/import', { method: 'POST', body: body })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        if (!res.ok) { showErrors(res.body.errors || ['Could not read that file.']); return; }
        if (!res.body.series.length) { showErrors(['No rows found in that file.']); return; }
        $('rows').innerHTML = res.body.series.map(rowHtml).join('');
        var st = res.body.settings || {};
        if (st.capacity) $('capacity').value = Math.round(st.capacity);
        if (st.ratio) $('ratio').value = st.ratio;
        if (st.threshold) $('threshold').value = st.threshold;
        if (st.facility) $('facility').value = Math.round(st.facility);
        if (!$('plan-name').value.trim() || $('plan-name').value === d.example.name) $('plan-name').value = f.name.replace(/\.(csv|xlsx)$/i, '');
        refresh();
      })
      .catch(function () { showErrors(['Could not upload that file. Check your connection.']); });
  });
  $('export-xlsx').addEventListener('click', function (e) { HP.exportXlsx({ kind: 'plan', payload: readState() }, e.currentTarget); });
  $('download-csv').addEventListener('click', function () {
    var s = readState();
    var blob = new Blob([toCsv(s)], { type: 'text/csv' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (s.name || 'coldflow-plan').replace(/[^\w\-]+/g, '-').toLowerCase() + '.csv';
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  });
  $('share').addEventListener('click', function () {
    var url = location.origin + location.pathname + '#d=' + encode(readState());
    var done = function () { $('share').textContent = 'Link copied'; setTimeout(function () { $('share').textContent = 'Copy share link'; }, 1800); };
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function () { prompt('Copy this link:', url); });
    else prompt('Copy this link:', url);
  });
  if ($('save')) $('save').addEventListener('click', save);
  window.addEventListener('beforeunload', function (e) {
    if (dirty && planId) { e.preventDefault(); e.returnValue = ''; }
  });

  // Lets the assistant read what's on screen.
  window.CF_getPlan = readState;

  // ---------- Start ----------
  var fromHash = location.hash.indexOf('#d=') === 0 ? decode(location.hash.slice(3)) : null;
  var start = (d.saved && d.saved.payload) || fromHash || d.example;
  // Fill any fields an older link might be missing.
  ['capacity', 'ratio', 'threshold', 'facility', 'intake_profile', 'release_profile'].forEach(function (k) {
    if (start[k] == null) start[k] = d.example[k];
  });
  setState(start);
  refresh();
})();
