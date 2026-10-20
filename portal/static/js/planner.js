// Capacity planner: inputs -> /api/scenario (Python engine) -> alert, stats, chart, table.
(function () {
  var d = HP.pageData();
  var scenario = d.scenario;
  var fmt = HP.fmt;
  var ICONS = { good: '●', warning: '▲', serious: '◆', critical: '■' };
  var LABELS = { good: 'Adequate', warning: 'Watch', serious: 'Strained', critical: 'Deficit' };
  var form = document.getElementById('planner-form');
  var inputs = ['season', 'capacity', 'ratio', 'threshold', 'facility', 'yield_shock', 'extra_capacity', 'tariff_change', 'tariff', 'kwh'].reduce(function (o, k) {
    o[k] = document.getElementById(k); return o;
  }, {});

  var chart = HP.chart('storage-chart', function () { return HP.storageConfig(scenario); });

  function bind(name, text) {
    var el = document.querySelector('[data-bind="' + name + '"]');
    if (el) el.textContent = text;
  }

  function showOutputs() {
    document.querySelector('[data-out="capacity"]').textContent = fmt.t(+inputs.capacity.value);
    document.querySelector('[data-out="ratio"]').textContent = fmt.pct(+inputs.ratio.value, 0);
    document.querySelector('[data-out="threshold"]').textContent = fmt.pct(+inputs.threshold.value, 0);
    document.querySelector('[data-out="facility"]').textContent = fmt.num(+inputs.facility.value) + ' t';
    HP.whatifOutputs();
  }

  function alertText(s) {
    var sim = s.simulation, i = s.inputs;
    switch (sim.status) {
      case 'critical':
        return ['Storage deficit in ' + sim.deficit_months.join(', ') + ' (' + i.season + ')',
          'Peak-harvest intake exceeds capacity by ' + fmt.t(sim.total_overflow_t) + '. That volume has no cold-chain slot and must be sold at harvest, moved out of the district, or held in ambient storage.'];
      case 'serious':
        return ['Capacity strained in ' + sim.alert_months.join(', ') + ' (' + i.season + ')',
          'Peak stock reaches ' + fmt.pct(sim.peak_utilisation) + ' of capacity, above the ' + fmt.pct(i.threshold, 0) + ' alert threshold. Little headroom for a bumper crop.'];
      case 'warning':
        return ['Approaching the threshold (' + i.season + ')',
          'Peak utilisation ' + fmt.pct(sim.peak_utilisation) + ' in ' + sim.peak_month + '. Watch arrivals through March.'];
      default:
        return ['Capacity adequate (' + i.season + ')',
          'Peak utilisation ' + fmt.pct(sim.peak_utilisation) + ' in ' + sim.peak_month + ', with ' + fmt.t(i.capacity - s.demand_t) + ' of headroom.'];
    }
  }

  function render(s) {
    var sim = s.simulation;
    var alertEl = document.getElementById('alert');
    alertEl.className = 'alert lvl-' + sim.status;
    alertEl.setAttribute('role', sim.status === 'critical' || sim.status === 'serious' ? 'alert' : 'status');
    var t = alertText(s);
    bind('alert-icon', ICONS[sim.status]);
    bind('alert-title', t[0]);
    bind('alert-body', t[1]);

    bind('production', fmt.t(s.production_t));
    bind('season-label', s.inputs.season);
    // Seasons already harvested but without verified figures are model estimates: mark them.
    var est = (s.seasons || []).some(function (o) { return o.value === s.inputs.season && /estimate$/.test(o.label); });
    document.querySelectorAll('[data-est-stat]').forEach(function (el) { el.classList.toggle('is-estimate', est); el.classList.toggle('hatch', est); });
    document.querySelectorAll('[data-est-tag]').forEach(function (el) { el.hidden = !est; });
    bind('demand', fmt.t(s.demand_t));
    bind('ratio-label', fmt.pct(s.inputs.ratio, 0) + ' of harvest');
    bind('coverage', fmt.pct(s.district_coverage, 1));
    bind('gap', s.facilities_to_close_gap > 0
      ? 'gap ≈ ' + fmt.num(Math.ceil(s.facilities_to_close_gap)) + ' facilities your size'
      : 'demand fully covered');
    bind('facility-cov', fmt.pct(s.facility_coverage, 2));
    bind('need', fmt.t(sim.capacity_needed_t));
    HP.renderEconomics(s, bind);
    bind('need-thr', fmt.t(sim.capacity_needed_threshold_t));

    var rows = sim.months.filter(function (m) { return m.peak_harvest; }).map(function (m) {
      return '<tr><td><strong>' + m.month + '</strong></td><td class="r">' + fmt.t(m.intake) + '</td><td class="r">' +
        fmt.t(m.demanded_stock) + '</td><td class="r">' + fmt.pct(m.utilisation) + '</td><td class="r"><span class="badge lvl-' +
        m.level + '"><i aria-hidden="true">' + ICONS[m.level] + '</i>' + LABELS[m.level] + '</span></td></tr>';
    });
    document.getElementById('peak-rows').innerHTML = rows.join('');
    renderImplications(s);
    chart.rebuild();
  }

  var timer = null;
  var seq = 0;
  function query() {
    var p = new URLSearchParams();
    Object.keys(inputs).forEach(function (k) { p.set(k, inputs[k].value); });
    return p;
  }
  function refresh() {
    refreshAllocation();
    showOutputs();
    clearTimeout(timer);
    timer = setTimeout(function () {
      var p = query();
      var mine = ++seq;
      fetch('/api/scenario?' + p.toString())
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (s) {
          if (mine !== seq) return; // a newer request superseded this one
          scenario = s;
          render(s);
          history.replaceState(null, '', location.pathname + '?' + p.toString());
        })
        .catch(function () { bind('alert-body', 'Could not reach the planner service. Check your connection and try again.'); });
    }, 120);
  }

  form.addEventListener('input', refresh);
  form.addEventListener('change', refresh);
  document.getElementById('reset').addEventListener('click', function () {
    inputs.season.selectedIndex = 0;
    Object.keys(d.defaults).forEach(function (k) { inputs[k].value = d.defaults[k]; });
    refresh();
  });

  document.querySelectorAll('[data-export="hathras"]').forEach(function (b) {
    b.addEventListener('click', function () {
      var p = {}; Object.keys(inputs).forEach(function (k) { p[k] = inputs[k].value; });
      HP.exportXlsx({ kind: 'hathras', params: p }, b);
    });
  });

  // ---------- Practical implications (all derived from the scenario response) ----------
  function esc(x) { return String(x).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function renderImplications(s) {
    var sim = s.simulation, i = s.inputs, e = s.economics, items = [];
    var cap = i.total_capacity || i.capacity;
    if (sim.total_overflow_t > 0) {
      items.push('<strong>' + fmt.t(sim.total_overflow_t) + '</strong> (' + fmt.pct(sim.total_overflow_t / s.production_t, 1) +
        ' of the harvest) has no cold-storage slot in ' + esc(sim.deficit_months.join(', ')) +
        '. It must be sold at harvest prices, moved out of the district, or held in ambient storage.');
      items.push('Closing the gap needs <strong>' + fmt.t(sim.capacity_gap_t) + '</strong> more capacity (about ' +
        fmt.num(Math.ceil(s.facilities_to_close_gap)) + ' facilities of ' + fmt.num(i.facility) + ' t), or <strong>' +
        fmt.t(Math.max(sim.capacity_needed_threshold_t - cap, 0)) + '</strong> to keep the peak under your ' + fmt.pct(i.threshold, 0) + ' alert level.');
      var fitShare = cap / s.production_t;
      items.push('Alternatively, storing at most <strong>' + fmt.pct(fitShare, 1) + '</strong> of the harvest (instead of ' + fmt.pct(i.ratio, 0) +
        ') would fit current capacity.');
    } else {
      items.push('Capacity covers the season: peak use is <strong>' + fmt.pct(sim.peak_utilisation, 1) + '</strong> in ' + esc(sim.peak_month) +
        ', leaving <strong>' + fmt.t(cap - sim.capacity_needed_t) + '</strong> of headroom.');
      if (sim.peak_utilisation >= i.threshold) items.push('But the peak is above your ' + fmt.pct(i.threshold, 0) + ' alert level, so a slightly larger crop or late loading could tip it into deficit.');
    }
    var short = s.blocks.filter(function (b) { return b.gap_t < 0; }).sort(function (a, b) { return a.gap_t - b.gap_t; });
    var spare = s.blocks.filter(function (b) { return b.gap_t > 0; }).sort(function (a, b) { return b.gap_t - a.gap_t; });
    if (short.length) items.push('Most strained blocks: ' + short.slice(0, 3).map(function (b) { return esc(b.name) + ' (' + fmt.t(-b.gap_t) + ' short)'; }).join(', ') +
      (spare.length ? '. Spare space: ' + spare.map(function (b) { return esc(b.name) + ' (' + fmt.t(b.gap_t) + ')'; }).join(', ') + '. See the redistribution plan below.' : '. No block has spare space.') +
      ' <span class="tag">Modelled block split</span>');
    items.push('Holding the stored stock costs about <strong>' + HP.rs(e.season_cost_rs) + '</strong> in electricity (' + HP.rs(e.cost_per_t_stored_rs) +
      ' per tonne) at ₹' + e.rate_rs_kwh.toFixed(2) + '/kWh. <span class="tag">Placeholder tariff</span>');
    document.getElementById('impl-list').innerHTML = items.map(function (x) { return '<li>' + x + '</li>'; }).join('');
  }

  // ---------- Scenario comparison (saved in this browser) ----------
  var KEY = 'cf-hathras-scenarios', MAX = 4;
  function loadSaved() { try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { return []; } }
  function store(list) { try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) { /* storage blocked: keep in memory */ } saved = list; }
  var saved = loadSaved();

  function describe(inp) {
    var parts = [inp.season];
    if (+inp.yield_shock) parts.push('yield ' + (+inp.yield_shock > 0 ? '+' : '') + Math.round(inp.yield_shock * 100) + '%');
    if (+inp.extra_capacity) parts.push('+' + fmt.t(+inp.extra_capacity) + ' capacity');
    if (+inp.capacity !== 950000) parts.push('base ' + fmt.t(+inp.capacity));
    if (+inp.ratio !== 0.75) parts.push(Math.round(inp.ratio * 100) + '% stored');
    if (+inp.tariff_change) parts.push('tariff ' + (+inp.tariff_change > 0 ? '+' : '') + Math.round(inp.tariff_change * 100) + '%');
    return parts.join(' · ');
  }
  function snapshot(s) {
    var inp = {}; Object.keys(inputs).forEach(function (k) { inp[k] = inputs[k].value; });
    var sim = s.simulation;
    return {
      inputs: inp, label: describe(inp),
      m: { harvest: s.production_t, demand: s.demand_t, capacity: s.inputs.total_capacity, peak: sim.peak_utilisation,
           unmet: sim.total_overflow_t, gap: sim.capacity_gap_t, need: sim.capacity_needed_t,
           cost: s.economics.season_cost_rs, cost_t: s.economics.cost_per_t_stored_rs, status: sim.status },
    };
  }
  var ROWS = [
    ['Harvest', 'harvest', fmt.t], ['Storage demand', 'demand', fmt.t], ['Capacity (incl. new)', 'capacity', fmt.t],
    ['Peak utilisation', 'peak', function (v) { return fmt.pct(v, 1); }], ['Without cold storage', 'unmet', fmt.t],
    ['Capacity gap', 'gap', fmt.t], ['Power cost (season)', 'cost', HP.rs], ['Power cost per tonne', 'cost_t', HP.rs],
  ];
  function delta(key, v, ref) {
    if (ref == null || v === ref) return '';
    var dlt = v - ref;
    var txt = key === 'peak' ? (dlt > 0 ? '+' : '') + (dlt * 100).toFixed(1) + ' pts'
      : (key === 'cost' || key === 'cost_t') ? (dlt > 0 ? '+' : '−') + HP.rs(Math.abs(dlt)) : (dlt > 0 ? '+' : '−') + fmt.t(Math.abs(dlt));
    var worse = (key === 'unmet' || key === 'gap' || key === 'peak' || key === 'cost' || key === 'cost_t') ? dlt > 0 : null;
    return '<br><span class="xs ' + (worse === null ? 'muted' : worse ? 'down' : 'up') + '">' + txt + '</span>';
  }
  function renderCompare() {
    var card = document.getElementById('compare-card');
    card.hidden = !saved.length;
    if (!saved.length) return;
    var head = '<thead><tr><th>Scenario</th>' + saved.map(function (sc, i) {
      return '<th class="r" style="white-space:normal;min-width:150px">' + String.fromCharCode(65 + i) + (i === 0 ? ' (reference)' : '') +
        '<br><span class="xs muted" style="text-transform:none;letter-spacing:0">' + esc(sc.label) + '</span></th>';
    }).join('') + '</tr></thead>';
    var ref = saved[0].m;
    var body = ROWS.map(function (r) {
      return '<tr><td>' + r[0] + '</td>' + saved.map(function (sc, i) {
        return '<td class="r">' + r[2](sc.m[r[1]]) + (i ? delta(r[1], sc.m[r[1]], ref[r[1]]) : '') + '</td>';
      }).join('') + '</tr>';
    }).join('');
    body += '<tr><td>Status</td>' + saved.map(function (sc) {
      return '<td class="r"><span class="badge lvl-' + sc.m.status + '"><i aria-hidden="true">' + ICONS[sc.m.status] + '</i>' + LABELS[sc.m.status] + '</span></td>';
    }).join('') + '</tr>';
    body += '<tr class="no-print"><td></td>' + saved.map(function (sc, i) {
      return '<td class="r"><button type="button" class="btn btn-ghost btn-sm" data-load="' + i + '">Load</button> <button type="button" class="btn btn-ghost btn-sm" data-remove="' + i + '">Remove</button></td>';
    }).join('') + '</tr>';
    document.getElementById('compare-table').innerHTML = head + '<tbody>' + body + '</tbody>';
  }
  document.getElementById('save-scenario').addEventListener('click', function () {
    var list = saved.slice();
    if (list.length >= MAX) list.splice(1, 1); // keep the reference, drop the oldest comparison
    list.push(snapshot(scenario));
    store(list); renderCompare();
    document.getElementById('compare-card').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });
  document.getElementById('clear-scenarios').addEventListener('click', function () { store([]); renderCompare(); });
  document.getElementById('compare-table').addEventListener('click', function (e) {
    var ld = e.target.closest('[data-load]'), rm = e.target.closest('[data-remove]');
    if (ld) {
      var inp = saved[+ld.dataset.load].inputs;
      Object.keys(inp).forEach(function (k) { if (inputs[k]) inputs[k].value = inp[k]; });
      refresh();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (rm) {
      var list = saved.slice(); list.splice(+rm.dataset.remove, 1); store(list); renderCompare();
    }
  });

  // ---------- Redistribution plan (LP on the server) ----------
  var alSeq = 0, alTimer = null;
  var alInputs = ['max_km', 'road_factor', 'rate'].map(function (id) { return document.getElementById(id); });
  function refreshAllocation() {
    clearTimeout(alTimer);
    alTimer = setTimeout(function () {
      var p = new URLSearchParams();
      Object.keys(inputs).forEach(function (k) { p.set(k, inputs[k].value); });
      alInputs.forEach(function (el) { if (el.value !== '') p.set(el.id, el.value); });
      var mine = ++alSeq;
      fetch('/api/allocation?' + p.toString())
        .then(function (r) { return r.json(); })
        .then(function (a) { if (mine === alSeq) renderAllocation(a); })
        .catch(function () { bind('al-basis', 'Could not reach the optimiser. Check your connection.'); });
    }, 150);
  }
  function renderAllocation(a) {
    if (!a.ok) { bind('al-basis', a.error || 'The optimiser is unavailable.'); return; }
    bind('al-stored', fmt.t(a.stored_t));
    bind('al-local', 'vs ' + fmt.t(a.local_only_stored_t) + ' if each block uses only its own stores');
    bind('al-gain', fmt.t(a.gain_t));
    bind('al-moved', fmt.t(a.moved_t) + ' moved between blocks');
    bind('al-tkm', fmt.num(a.tonne_km) + ' t-km');
    bind('al-avg', a.moved_t ? 'average ' + a.avg_haul_km.toFixed(1) + ' km per tonne moved' : 'no transfers needed');
    bind('al-cost', a.freight_cost_rs != null ? HP.rs(a.freight_cost_rs) : '—');
    bind('al-cost-note', a.freight_cost_rs != null ? '@ ₹' + a.rate_rs_per_tkm + '/t-km (your rate)' : 'enter your freight rate');
    var rows = a.transfers.map(function (f) {
      return '<tr><td>' + esc(f.from_name) + '</td><td>' + esc(f.to_name) + '</td><td class="r">' + fmt.t(f.tonnes) + '</td><td class="r">' + f.km.toFixed(1) + ' km</td></tr>';
    });
    document.getElementById('al-transfers').innerHTML = rows.length
      ? '<thead><tr><th>From block</th><th>To block</th><th class="r">Tonnes</th><th class="r">Distance</th></tr></thead><tbody>' + rows.join('') + '</tbody>'
      : '<tbody><tr><td class="muted">No transfers: every block either fits its own produce or no spare space is within reach.</td></tr></tbody>';
    var left = a.nodes.filter(function (n) { return n.unstored_t > 0.5; }).sort(function (x, y) { return y.unstored_t - x.unstored_t; });
    bind('al-left', left.length
      ? 'Still without storage after redistribution: ' + left.map(function (n) { return n.name + ' ' + fmt.t(n.unstored_t); }).join(', ') +
        '. New capacity there would relieve the most strain.'
      : 'Every block\'s produce finds storage within the haul limit.');
    bind('al-basis', a.data_basis + ' Solver: ' + a.solver + '. Single-period peak model; it does not schedule trucks or price individual stores.');
  }
  alInputs.forEach(function (el) { el.addEventListener('input', refreshAllocation); });

  showOutputs();
  render(scenario);
  renderCompare();
  refreshAllocation();
})();
