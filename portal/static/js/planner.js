// Capacity planner: inputs -> /api/scenario (Python engine) -> alert, stats, chart, table.
(function () {
  var d = HP.pageData();
  var scenario = d.scenario;
  var fmt = HP.fmt;
  var ICONS = { good: '●', warning: '▲', serious: '◆', critical: '■' };
  var LABELS = { good: 'Adequate', warning: 'Watch', serious: 'Strained', critical: 'Deficit' };
  var form = document.getElementById('planner-form');
  var inputs = ['season', 'capacity', 'ratio', 'threshold', 'facility'].reduce(function (o, k) {
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
    bind('demand', fmt.t(s.demand_t));
    bind('ratio-label', fmt.pct(s.inputs.ratio, 0) + ' of harvest');
    bind('coverage', fmt.pct(s.district_coverage, 1));
    bind('gap', s.facilities_to_close_gap > 0
      ? 'gap ≈ ' + fmt.num(Math.ceil(s.facilities_to_close_gap)) + ' facilities your size'
      : 'demand fully covered');
    bind('facility-cov', fmt.pct(s.facility_coverage, 2));
    bind('need', fmt.t(sim.capacity_needed_t));
    bind('need-thr', fmt.t(sim.capacity_needed_threshold_t));

    var rows = sim.months.filter(function (m) { return m.peak_harvest; }).map(function (m) {
      return '<tr><td><strong>' + m.month + '</strong></td><td class="r">' + fmt.t(m.intake) + '</td><td class="r">' +
        fmt.t(m.demanded_stock) + '</td><td class="r">' + fmt.pct(m.utilisation) + '</td><td class="r"><span class="badge lvl-' +
        m.level + '"><i aria-hidden="true">' + ICONS[m.level] + '</i>' + LABELS[m.level] + '</span></td></tr>';
    });
    document.getElementById('peak-rows').innerHTML = rows.join('');
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

  showOutputs();
  render(scenario);
})();
