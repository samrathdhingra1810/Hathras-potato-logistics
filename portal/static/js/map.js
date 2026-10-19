// Block strain map: Leaflet markers sized by demand, coloured by strain level.
(function () {
  var d = JSON.parse(document.getElementById('page-data').textContent);
  var scenario = d.scenario;
  // SVG marker attributes need literal colors; status hexes are mode-invariant.
  var STATUS = { good: '#0ca30c', warning: '#fab219', serious: '#ec835a', critical: '#d03b3b' };
  var ICONS = { good: '●', warning: '▲', serious: '◆', critical: '■' };
  var LABELS = { good: 'Adequate', warning: 'Watch', serious: 'Strained', critical: 'Deficit' };
  function t(v) {
    var a = Math.abs(v);
    if (a >= 1e6) return (v / 1e6).toFixed(2) + 'M t';
    if (a >= 1e3) return (v / 1e3).toFixed(a >= 1e5 ? 0 : 1) + 'k t';
    return Math.round(v) + ' t';
  }
  function pct(v, dg) { return (v * 100).toFixed(dg == null ? 1 : dg) + '%'; }
  function surface() { return getComputedStyle(document.documentElement).getPropertyValue('--surface').trim(); }

  var map = L.map('map', { scrollWheelZoom: false }).setView([d.center.lat, d.center.lng], 10);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);

  var legend = L.control({ position: 'bottomleft' });
  legend.onAdd = function () {
    var div = L.DomUtil.create('div', 'map-legend');
    div.innerHTML = '<b>Strain level</b><br>' + Object.keys(LABELS).map(function (k) {
      return '<span style="color:' + STATUS[k] + '">' + ICONS[k] + '</span> ' + LABELS[k];
    }).join('<br>') + '<br><span>Size ∝ storage demand</span>';
    return div;
  };
  legend.addTo(map);

  var layer = L.layerGroup().addTo(map);

  function render(s) {
    layer.clearLayers();
    var max = Math.max.apply(null, s.blocks.map(function (b) { return b.demand_t; }));
    s.blocks.forEach(function (b) {
      var popup = '<strong>' + b.name + ' block</strong><br>Storage demand: ' + t(b.demand_t) +
        '<br>Local capacity: ' + t(b.capacity_t) + '<br>Utilisation: ' + pct(b.utilisation) +
        '<br>' + (b.gap_t >= 0 ? 'Headroom ' + t(b.gap_t) : 'Shortfall ' + t(-b.gap_t));
      L.circleMarker([b.lat, b.lng], {
        radius: 10 + 18 * Math.sqrt(b.demand_t / max),
        color: surface(), weight: 2, fillColor: STATUS[b.level], fillOpacity: 0.8,
      }).bindTooltip(b.name, { permanent: true, direction: 'top', offset: [0, -8] })
        .bindPopup(popup).addTo(layer);
    });

    var rows = s.blocks.slice().sort(function (a, b) { return b.utilisation - a.utilisation; }).map(function (b) {
      return '<tr><td><strong>' + b.name + '</strong></td><td class="r">' + t(b.demand_t) + '</td><td class="r">' +
        t(b.capacity_t) + '</td><td class="r">' + pct(b.utilisation, 0) + '</td><td class="r"><span class="badge lvl-' +
        b.level + '"><i aria-hidden="true">' + ICONS[b.level] + '</i>' + LABELS[b.level] + '</span></td></tr>';
    });
    document.getElementById('block-rows').innerHTML = rows.join('');
    document.querySelector('[data-bind="caption"]').textContent = s.inputs.season + ' · capacity ' + t(s.inputs.capacity);
  }

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
          scenario = s; render(s);
          history.replaceState(null, '', location.pathname + '?' + p.toString());
        })
        .catch(function () { /* keep the last good render */ });
    }, 120);
  }
  [season, capacity, ratio].forEach(function (el) { el.addEventListener('input', refresh); });
  document.addEventListener('themechange', function () { render(scenario); });

  outputs();
  render(scenario);
})();
