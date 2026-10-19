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

  // Landing: solid nav once the splash scrolls away.
  if (document.body.classList.contains('landing') && nav) {
    var onScroll = function () { nav.classList.toggle('scrolled', window.scrollY > 40); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

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
})();
