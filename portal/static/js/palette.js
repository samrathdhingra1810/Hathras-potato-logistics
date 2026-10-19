// Command palette (Ctrl/Cmd + K): jump to any page or run an action; free text asks the assistant.
(function () {
  var root = document.getElementById('palette');
  if (!root || !window.CF) return;
  var input = document.getElementById('palette-input');
  var list = document.getElementById('palette-list');
  var r = window.CF.routes;
  var go = function (href) { return function () { window.CF.navigate ? window.CF.navigate(href) : (location.href = href); }; };

  var items = [
    { group: 'Start', label: 'Plan with your own data', hint: 'Forecast & storage for any district', run: go(r.plan), k: 'new plan custom upload csv' },
    { group: 'Start', label: 'Ask the assistant', hint: 'AI help with any question', run: function () { window.CFAssistant && window.CFAssistant.open(); }, k: 'ai chat help question' },
    { group: 'Hathras', label: 'Hathras overview', hint: 'District dashboard', run: go(r.hathras), k: 'district home example' },
    { group: 'Hathras', label: 'Capacity planner', hint: 'What-if storage capacity', run: go(r.planner), k: 'storage deficit simulate' },
    { group: 'Hathras', label: 'Harvest forecast', hint: '2024-25 and 2025-26', run: go(r.forecast), k: 'predict trend regression' },
    { group: 'Hathras', label: 'Production analytics', hint: 'Area, output, yield', run: go(r.production), k: 'yield area chart' },
    { group: 'Hathras', label: 'Block strain map', hint: 'Seven development blocks', run: go(r.map), k: 'gis blocks sasni sadabad sikandra' },
    { group: 'Data', label: 'Data & downloads', hint: 'Dataset, assumptions, API', run: go(r.data), k: 'api json assumptions' },
    { group: 'Data', label: 'Download Hathras CSV', hint: 'production.csv', run: go(r.csv), k: 'export file' },
    { group: 'Info', label: 'Methodology', hint: 'How the numbers are made', run: go(r.about + '#methodology'), k: 'about method how' },
    { group: 'Info', label: 'Services', hint: 'What ColdFlow offers', run: go(r.services), k: 'features' },
    { group: 'Info', label: 'Home', hint: '', run: go(r.home), k: 'start landing' },
    { group: 'Settings', label: 'Toggle dark mode', hint: '', run: function () { document.getElementById('theme-toggle').click(); }, k: 'theme light dark' },
  ];
  if (window.CF.accounts) {
    if (window.CF.signedIn) {
      items.push({ group: 'Account', label: 'Dashboard', hint: 'Your saved plans', run: go(r.dashboard), k: 'plans saved' });
      items.push({ group: 'Account', label: 'Account settings', hint: '', run: go(r.account), k: 'password profile' });
    } else {
      items.push({ group: 'Account', label: 'Log in', hint: '', run: go(r.login), k: 'sign in' });
      items.push({ group: 'Account', label: 'Create account', hint: 'Save plans', run: go(r.signup), k: 'sign up register' });
    }
  }

  var shown = [], active = 0;
  function score(it, q) {
    var hay = (it.label + ' ' + it.hint + ' ' + it.group + ' ' + it.k).toLowerCase();
    var words = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length) return 1;
    var s = 0;
    for (var i = 0; i < words.length; i++) {
      var at = hay.indexOf(words[i]);
      if (at < 0) return 0;
      s += at === 0 || it.label.toLowerCase().indexOf(words[i]) === 0 ? 3 : 1;
    }
    return s;
  }
  function render() {
    var q = input.value.trim();
    shown = items.map(function (it) { return { it: it, s: score(it, q) }; })
      .filter(function (x) { return x.s > 0; })
      .sort(function (a, b) { return b.s - a.s; })
      .map(function (x) { return x.it; });
    if (q) shown.push({ group: 'Assistant', label: 'Ask: “' + q + '”', hint: 'Send to the assistant', ask: q,
                        run: function () { window.CFAssistant && window.CFAssistant.open(q, true); } });
    active = Math.min(active, Math.max(shown.length - 1, 0));
    var last = '';
    list.innerHTML = shown.map(function (it, i) {
      var head = it.group !== last ? '<li class="palette-group" role="presentation">' + it.group + '</li>' : '';
      last = it.group;
      return head + '<li role="option" id="pal-' + i + '" data-i="' + i + '" aria-selected="' + (i === active) + '">' +
        '<span>' + escapeHtml(it.label) + '</span><small>' + escapeHtml(it.hint || '') + '</small></li>';
    }).join('') || '<li class="palette-empty">No matches</li>';
    input.setAttribute('aria-activedescendant', 'pal-' + active);
    var el = document.getElementById('pal-' + active);
    if (el) el.scrollIntoView({ block: 'nearest' });
  }
  function escapeHtml(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function open() {
    root.hidden = false;
    requestAnimationFrame(function () { root.classList.add('open'); });
    input.value = ''; active = 0; render();
    setTimeout(function () { input.focus(); }, 20);
  }
  function close() {
    root.classList.remove('open');
    setTimeout(function () { root.hidden = true; }, 150);
  }
  function choose(i) {
    var it = shown[i];
    if (!it) return;
    close();
    it.run();
  }

  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      root.classList.contains('open') ? close() : open();
    } else if (root.classList.contains('open')) {
      if (e.key === 'Escape') { e.preventDefault(); close(); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, shown.length - 1); render(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); render(); }
      else if (e.key === 'Enter') { e.preventDefault(); choose(active); }
    }
  });
  input.addEventListener('input', function () { active = 0; render(); });
  list.addEventListener('click', function (e) {
    var li = e.target.closest('[data-i]');
    if (li) choose(+li.dataset.i);
  });
  root.querySelector('[data-palette-close]').addEventListener('click', close);
  document.querySelectorAll('[data-open-palette]').forEach(function (b) { b.addEventListener('click', open); });
  // Show the right shortcut label on non-Apple keyboards.
  if (!/Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)) {
    document.querySelectorAll('kbd').forEach(function (k) { if (k.textContent === '⌘K') k.textContent = 'Ctrl K'; else if (k.textContent === '⌘') k.textContent = 'Ctrl'; });
  }
})();
