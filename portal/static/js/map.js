// Block strain map: diverging heatmap by month, click-through block details, distances.
(function () {
  var d = JSON.parse(document.getElementById('page-data').textContent);
  var scenario = d.scenario;
  var month = 'peak';
  var selected = null;
  var ICONS = { good: '●', warning: '▲', serious: '◆', critical: '■' };
  var LABELS = { good: 'Adequate', warning: 'Watch', serious: 'Strained', critical: 'Deficit' };
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  function t(v) {
    var a = Math.abs(v);
    if (a >= 1e6) return (v / 1e6).toFixed(2) + 'M t';
    if (a >= 1e3) return (v / 1e3).toFixed(a >= 1e5 ? 0 : 1) + 'k t';
    return Math.round(v) + ' t';
  }
  function pct(v, dg) { return (v * 100).toFixed(dg == null ? 1 : dg) + '%'; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function surface() { return getComputedStyle(document.documentElement).getPropertyValue('--surface').trim(); }

  // Diverging scale: blue = spare, grey = exactly full, red = short. Literal hex (SVG attributes).
  var STOPS = [[0.4, [28, 92, 171]], [0.75, [109, 167, 236]], [1.0, [195, 194, 183]], [1.25, [236, 131, 90]], [1.6, [180, 35, 35]]];
  function heat(u) {
    u = Math.max(STOPS[0][0], Math.min(STOPS[STOPS.length - 1][0], u));
    for (var i = 1; i < STOPS.length; i++) {
      if (u <= STOPS[i][0]) {
        var a = STOPS[i - 1], b = STOPS[i], k = (u - a[0]) / (b[0] - a[0]);
        var c = a[1].map(function (x, j) { return Math.round(x + (b[1][j] - x) * k); });
        return 'rgb(' + c.join(',') + ')';
      }
    }
    return 'rgb(180,35,35)';
  }
  function utilFor(b) {
    if (month === 'peak') return b.utilisation;
    var m = b.monthly.filter(function (x) { return x.month === month; })[0];
    return m ? m.utilisation : 0;
  }
  function levelFor(u) {
    var thr = scenario.inputs.threshold;
    return u > 1 ? 'critical' : u >= thr ? 'serious' : u >= thr - 0.15 ? 'warning' : 'good';
  }

  var map = L.map('map', { scrollWheelZoom: false }).setView([d.center.lat, d.center.lng], 10);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  var layer = L.layerGroup().addTo(map);

  function render() {
    layer.clearLayers();
    var max = Math.max.apply(null, scenario.blocks.map(function (b) { return b.demand_t; }));
    scenario.blocks.forEach(function (b) {
      var u = utilFor(b);
      var marker = L.circleMarker([b.lat, b.lng], {
        radius: 11 + 18 * Math.sqrt(b.demand_t / max),
        color: selected === b.id ? '#0f1419' : surface(), weight: selected === b.id ? 3 : 2,
        fillColor: heat(u), fillOpacity: 0.85,
      }).bindTooltip(b.name + ' · ' + pct(u, 0), { permanent: true, direction: 'top', offset: [0, -8] });
      marker.on('click', function () { select(b.id); });
      marker.addTo(layer);
    });

    var only = filterIds();
    var shown = scenario.blocks.filter(function (b) { return !only || only.indexOf(b.id) >= 0; });
    var rows = shown.slice().sort(function (a, b) { return utilFor(b) - utilFor(a); }).map(function (b) {
      var u = utilFor(b), lv = levelFor(u);
      return '<tr data-id="' + b.id + '"' + (selected === b.id ? ' class="sel"' : '') + '><td><strong>' + esc(b.name) + '</strong></td><td class="r">' +
        t(b.demand_t) + '</td><td class="r">' + t(b.capacity_t) + '</td><td class="r">' + pct(u, 1) +
        '</td><td class="r"><span class="badge lvl-' + lv + '"><i aria-hidden="true">' + ICONS[lv] + '</i>' + LABELS[lv] + '</span></td></tr>';
    });
    document.getElementById('block-rows').innerHTML = rows.length ? rows.join('')
      : '<tr><td colspan="5" class="muted">No block matches “' + esc(filterEl.value) + '”.</td></tr>';
    document.querySelector('[data-bind="caption"]').textContent = scenario.inputs.season + ' · ' +
      (month === 'peak' ? 'peak month' : month) + ' · capacity ' + t(scenario.inputs.total_capacity || scenario.inputs.capacity);
    if (selected) detail(selected);
  }

  // Block filter (typed or spoken). Matches English and Hindi names and common spellings.
  var filterEl = document.getElementById('block-filter');
  function filterIds() {
    var q = filterEl ? filterEl.value.trim().toLowerCase() : '';
    if (!q) return null;
    var blocks = (window.CF && CF.blocks) || [];
    var hits = blocks.filter(function (b) {
      return [b.name, b.hi].concat(b.aliases || []).some(function (n) { return String(n).toLowerCase().indexOf(q) >= 0; });
    }).map(function (b) { return b.id; });
    if (!hits.length && window.CFVoice) { var m = CFVoice.matchBlock(q); if (m) hits = [m.id]; }
    return hits;
  }
  if (filterEl) filterEl.addEventListener('input', function () {
    var only = filterIds();
    if (only && only.length === 1 && selected !== only[0]) { select(only[0]); return; }
    render();
  });

  function detail(id) {
    var b = scenario.blocks.filter(function (x) { return x.id === id; })[0];
    var card = document.getElementById('block-detail');
    if (!b) { card.hidden = true; return; }
    card.hidden = false;
    var set = function (k, v) { card.querySelector('[data-bind="' + k + '"]').textContent = v; };
    set('bd-name', b.name + ' block');
    set('bd-sub', 'Peak ' + pct(b.utilisation, 1) + ' of local capacity · ' + LABELS[b.level]);
    set('bd-demand', t(b.demand_t));
    set('bd-capacity', t(b.capacity_t));
    set('bd-gap', b.gap_t >= 0 ? t(b.gap_t) + ' spare' : t(-b.gap_t) + ' short');
    var top = Math.max(1.2, Math.max.apply(null, b.monthly.map(function (m) { return m.utilisation; })));
    card.querySelector('[data-bind-html="bd-months"]').innerHTML = b.monthly.map(function (m) {
      return '<div class="col" title="' + m.month + ': ' + pct(m.utilisation, 0) + '"><span style="--c:' + heat(m.utilisation) +
        ';height:' + (m.utilisation / top * 100).toFixed(1) + '%"></span><i>' + m.month[0] + '</i></div>';
    }).join('');
    var near = b.nearest_headroom || [];
    card.querySelector('[data-bind-html="bd-near"]').innerHTML = near.length
      ? near.map(function (n) { return '<li><span>' + esc(n.name) + ' · ' + n.km + ' km</span><strong>' + t(n.headroom_t) + ' spare</strong></li>'; }).join('')
      : '<li><span>No block has spare capacity at this setting.</span></li>';
    var h = (d.nhb || {})[id];
    var box = card.querySelector('[data-bind-html="bd-nhb"]');
    if (box) box.innerHTML = h && h.count
      ? '<strong>' + h.count + ' record' + (h.count === 1 ? '' : 's') + '</strong>' + (h.years ? ', sanctioned ' + h.years[0] + (h.years[1] !== h.years[0] ? '–' + h.years[1] : '') : '') +
        (h.cap ? ', ' + Math.round(h.cap).toLocaleString('en-IN') + ' MT at sanction' : '') + ': ' + h.records.map(esc).join(', ')
      : 'No NHB record names this block in its address.';
  }

  function select(id) {
    selected = id;
    render();
    var card = document.getElementById('block-detail');
    if (window.innerWidth < 980) card.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  document.getElementById('block-rows').addEventListener('click', function (e) {
    var tr = e.target.closest('tr[data-id]');
    if (tr) select(tr.dataset.id);
  });
  document.querySelector('[data-bd-close]').addEventListener('click', function () { selected = null; document.getElementById('block-detail').hidden = true; render(); });

  // Month buttons
  var seg = document.querySelector('[data-seg="month"]');
  seg.addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-value]');
    if (!btn) return;
    seg.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-checked', String(b === btn)); });
    month = btn.dataset.value;
    render();
  });

  // Distance matrix
  (function () {
    var ids = scenario.blocks.map(function (b) { return b.id; });
    var name = {}; scenario.blocks.forEach(function (b) { name[b.id] = b.name; });
    var html = '<thead><tr><th></th>' + ids.map(function (i) { return '<th class="r">' + esc(name[i]) + '</th>'; }).join('') + '</tr></thead><tbody>' +
      ids.map(function (a) {
        return '<tr><td><strong>' + esc(name[a]) + '</strong></td>' + ids.map(function (b) {
          return '<td class="r' + (a === b ? ' muted' : '') + '">' + (a === b ? '—' : d.distances[a][b] + ' km') + '</td>';
        }).join('') + '</tr>';
      }).join('') + '</tbody>';
    document.getElementById('dist-table').innerHTML = html;
  })();

  // Controls -> server scenario
  var season = document.getElementById('season');
  var capacity = document.getElementById('capacity');
  var ratio = document.getElementById('ratio');
  function outputs() {
    document.querySelector('[data-out="capacity"]').textContent = t(+capacity.value);
    document.querySelector('[data-out="ratio"]').textContent = pct(+ratio.value, 0);
  }
  var timer = null, seq = 0;
  function refresh() {
    outputs();
    clearTimeout(timer);
    timer = setTimeout(function () {
      var p = new URLSearchParams({ season: season.value, capacity: capacity.value, ratio: ratio.value });
      var mine = ++seq;
      fetch('/api/scenario?' + p.toString())
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (s) {
          if (mine !== seq) return;
          scenario = s; render();
          history.replaceState(null, '', location.pathname + '?' + p.toString());
        })
        .catch(function () { /* keep the last good render */ });
    }, 120);
  }
  [season, capacity, ratio].forEach(function (el) { el.addEventListener('input', refresh); });
  document.addEventListener('themechange', render);

  outputs();
  render();
})();
