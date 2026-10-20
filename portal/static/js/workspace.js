// Workspaces: "your block" picker, directions, overflow by distance. Language comes from the header switch.
// Display only; every figure was rendered by the server from the scenario.
(function () {
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
  };

  var hiName = {};
  ((window.CF && CF.blocks) || []).forEach(function (b) { hiName[b.id] = b.hi; });
  function lang() { return window.CF && CF.lang ? CF.lang() : 'en'; }

  // Assistant prompt buttons.
  document.querySelectorAll('[data-ask-ws]').forEach(function (b) {
    b.addEventListener('click', function () { window.CFAssistant && window.CFAssistant.open(b.dataset.askWs, true); });
  });

  // Charts inside a closed <details> have no size until it opens.
  document.querySelectorAll('details').forEach(function (d) {
    d.addEventListener('toggle', function () { if (d.open && window.HP && HP.resizeAll) HP.resizeAll(); });
  });

  document.querySelectorAll('[data-field-view]').forEach(function (view) {
    var space, dist;
    try { space = JSON.parse(view.dataset.space); dist = JSON.parse(view.dataset.distances); } catch (e) { return; }
    var byId = {}; space.forEach(function (s) { byId[s.id] = s; });
    var select = view.querySelector('[data-fv-block]');
    if (!select) return;

    function apply(id) {
      if (!byId[id]) return;
      select.value = id;
      view.querySelectorAll('[data-fv-mine]').forEach(function (el) { el.hidden = el.dataset.fvMine !== id; });
      document.querySelectorAll('.fv-card[data-block]').forEach(function (c) { c.classList.toggle('is-mine', c.dataset.block === id); });

      // Directions: your own block if it has space, else the closest block that does.
      var dir = view.querySelector('[data-fv-directions]');
      if (dir) {
        var target = byId[id].spare_t > 0 ? byId[id] : space.filter(function (s) { return s.spare_t > 0; })
          .sort(function (a, b) { return dist[id][a.id] - dist[id][b.id]; })[0];
        if (target) {
          dir.href = 'https://www.google.com/maps/dir/?api=1&destination=' + target.lat + ',' + target.lng;
          var dest = dir.querySelector('[data-fv-dest]');
          if (dest) dest.textContent = target.name;
          var destHi = dir.querySelector('[data-fv-dest-hi]');
          if (destHi) destHi.textContent = hiName[target.id] || target.name;
        }
      }

      // Owner: overflow from the blocks closest to your store first.
      var list = view.querySelector('[data-fv-overflow]');
      if (list) {
        var items = Array.prototype.slice.call(list.children);
        items.sort(function (a, b) { return dist[id][a.dataset.block] - dist[id][b.dataset.block]; });
        items.forEach(function (li) {
          var km = dist[id][li.dataset.block];
          var hi = lang() === 'hi';
          li.querySelector('[data-km]').textContent = li.dataset.block === id ? (hi ? '· आपका ब्लॉक' : '· your block')
            : '· ' + km + (hi ? ' किमी दूर' : ' km from your block');
          list.appendChild(li);
        });
      }
    }

    select.addEventListener('change', function () { apply(select.value); store.set('cf-block', select.value); });
    document.addEventListener('cf:lang', function () { apply(select.value); });
    apply(store.get('cf-block') || select.value);
  });
})();
