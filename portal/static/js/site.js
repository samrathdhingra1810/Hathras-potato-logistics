// Site chrome: theme toggle, mobile menu, dropdowns, flash dismiss, password reveal.
(function () {
  var root = document.documentElement;

  function currentTheme() {
    var t = root.getAttribute('data-theme');
    if (t) return t;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  var themeBtn = document.getElementById('theme-toggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) { /* storage unavailable */ }
      document.dispatchEvent(new CustomEvent('themechange', { detail: next }));
    });
  }
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
      if (!root.getAttribute('data-theme')) document.dispatchEvent(new CustomEvent('themechange'));
    });
  }

  var nav = document.getElementById('nav');
  var menuBtn = document.getElementById('menu-toggle');
  if (menuBtn && nav) {
    menuBtn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', String(open));
      menuBtn.textContent = open ? '✕' : '☰';
    });
  }

  document.querySelectorAll('[data-dropdown]').forEach(function (btn) {
    var li = btn.closest('.has-dropdown');
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = li.classList.toggle('open');
      btn.setAttribute('aria-expanded', String(open));
    });
  });
  document.addEventListener('click', function () {
    document.querySelectorAll('.has-dropdown.open').forEach(function (li) {
      li.classList.remove('open');
      li.querySelector('[data-dropdown]').setAttribute('aria-expanded', 'false');
    });
  });

  document.querySelectorAll('[data-dismiss]').forEach(function (btn) {
    btn.addEventListener('click', function () { btn.parentElement.remove(); });
  });

  document.querySelectorAll('[data-pw-toggle]').forEach(function (btn) {
    var input = document.getElementById(btn.getAttribute('data-pw-toggle'));
    btn.addEventListener('click', function () {
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.textContent = show ? 'Hide' : 'Show';
      btn.setAttribute('aria-pressed', String(show));
    });
  });

  // ---- Page transitions ----
  // Browsers with cross-document View Transitions animate natively (see site.css);
  // the clicked tile morphs into the next page's header. Others get a short fade.
  var nativeVT = 'onpagereveal' in window;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!nativeVT) root.classList.add('no-vt');
  window.CF = window.CF || {};
  window.CF.navigate = function (href, fromEl) {
    if (nativeVT || reduce) {
      if (fromEl && nativeVT) fromEl.style.viewTransitionName = 'cf-hero';
      location.href = href;
      return;
    }
    document.body.classList.add('is-leaving');
    setTimeout(function () { location.href = href; }, 200);
  };
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[data-transition]');
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (a.origin !== location.origin || a.target === '_blank') return;
    if (a.pathname === location.pathname && a.hash) return;
    e.preventDefault();
    window.CF.navigate(a.href, a.matches('.cf-role, .cf-gw-link, .cf-btn') ? a : null);
  });
  // An interrupted transition (fast double navigation) is harmless; don't surface it as an error.
  ['pageswap', 'pagereveal'].forEach(function (ev) {
    window.addEventListener(ev, function (e) {
      if (e.viewTransition) ['ready', 'finished', 'updateCallbackDone'].forEach(function (k) { e.viewTransition[k].catch(function () {}); });
    });
  });
  // Restore after back/forward cache.
  window.addEventListener('pageshow', function () { document.body.classList.remove('is-leaving'); });

  // ---- Offline support (PWA) ----
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    window.addEventListener('load', function () { navigator.serviceWorker.register('/sw.js').catch(function () {}); });
  }
  function netBadge() { document.documentElement.classList.toggle('is-offline', !navigator.onLine); }
  window.addEventListener('online', netBadge); window.addEventListener('offline', netBadge); netBadge();

  // ---- Print / PDF report ----
  document.querySelectorAll('[data-print]').forEach(function (btn) {
    btn.addEventListener('click', function () { window.print(); });
  });
  window.addEventListener('beforeprint', function () {
    var d = new Date().toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
    document.querySelectorAll('[data-print-date]').forEach(function (el) { el.textContent = d; });
    if (window.HP && HP.resizeAll) HP.resizeAll();
  });
})();
