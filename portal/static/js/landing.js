// Landing splash: drifting supply-chain chips, Hathras clock, section dots.
(function () {
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- Floating chips ----
  var CHIPS = [
    ['आलू', 'en'], ['cold chain', 'en'], ['शीत भंडारण', 'hi'], ['2–4 °C', 'en'], ['harvest peak · March', 'en'],
    ['Hathras · 1.36M t', 'en'], ['Agra', 'en'], ['Kannauj', 'en'], ['Farrukhabad', 'en'], ['capacity 108%', 'warn'],
    ['forecast 2025-26', 'en'], ['फसल', 'hi'], ['deficit alert', 'warn'], ['storage demand', 'en'], ['Firozabad', 'en'],
    ['मंडी', 'hi'], ['release · Sep', 'en'], ['yield 24.7 t/ha', 'en'], ['किसान', 'hi'], ['Aligarh', 'en'],
    ['loading · Feb–Apr', 'en'], ['भंडार क्षमता', 'hi'], ['95% interval', 'en'], ['Sikandra Rao', 'en'],
  ];
  var host = document.getElementById('chips');
  if (host) {
    // Keep chips clear of the nav, the central wordmark, the footer row and each other.
    var taken = [];
    function spot(el) {
      var others = taken.filter(function (t) { return t.el !== el; });
      var narrow = window.innerWidth < 640;
      for (var i = 0; i < 60; i++) {
        var x = 3 + Math.random() * (narrow ? 62 : 84), y = 13 + Math.random() * 70;
        if (narrow ? (y > 30 && y < 70) : (x > 22 && x < 74 && y > 28 && y < 70)) continue;
        var clash = others.some(function (t) { return Math.abs(t.x - x) < (narrow ? 42 : 14) && Math.abs(t.y - y) < (narrow ? 6 : 7); });
        if (!clash) return [x, y];
      }
      return null;
    }
    var visible = window.innerWidth < 640 ? 7 : 16;
    var pool = CHIPS.slice().sort(function () { return Math.random() - 0.5; });
    var nodes = [];
    for (var i = 0; i < visible; i++) {
      var el = document.createElement('span');
      el.className = 'chip';
      host.appendChild(el);
      nodes.push(el);
    }
    var next = 0;
    function place(el, delay) {
      var c = pool[next++ % pool.length];
      var p = spot(el);
      taken = taken.filter(function (t) { return t.el !== el; });
      if (!p) { el.classList.remove('live'); setTimeout(function () { place(el, 0); }, 3000); return; }
      taken.push({ el: el, x: p[0], y: p[1] });
      el.textContent = c[0];
      el.dataset.kind = c[1];
      el.style.left = p[0] + '%';
      el.style.top = p[1] + '%';
      el.style.fontSize = (12 + Math.random() * 7).toFixed(1) + 'px';
      el.style.setProperty('--dx', (Math.random() * 40 - 20).toFixed(0) + 'px');
      el.style.setProperty('--dy', (Math.random() * 30 - 15).toFixed(0) + 'px');
      el.style.animationDelay = delay + 's';
      el.style.animationDuration = (9 + Math.random() * 6).toFixed(1) + 's';
      el.classList.remove('live');
      void el.offsetWidth; // restart the animation
      el.classList.add('live');
    }
    nodes.forEach(function (el, i) {
      place(el, reduceMotion ? 0 : -(Math.random() * 8));
      if (!reduceMotion) el.addEventListener('animationiteration', function () { place(el, 0); });
    });
  }

  // ---- Clock (Hathras is on IST) ----
  var clock = document.getElementById('clock');
  if (clock) {
    var tf = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' });
    var df = new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'Asia/Kolkata' });
    var tick = function () {
      var now = new Date();
      clock.querySelector('[data-clock-time]').textContent = tf.format(now);
      clock.querySelector('[data-clock-date]').textContent = df.format(now) + ' · Hathras';
    };
    tick();
    setInterval(tick, 15000);
  }

  // ---- Section dots ----
  var dots = document.getElementById('dots');
  var sections = Array.prototype.slice.call(document.querySelectorAll('[data-section]'));
  if (dots && sections.length) {
    var links = sections.map(function (s) {
      var a = document.createElement('a');
      a.href = '#' + s.id;
      a.setAttribute('aria-label', s.dataset.section);
      a.title = s.dataset.section;
      dots.appendChild(a);
      return a;
    });
    var setActive = function (id) {
      links.forEach(function (a) { a.classList.toggle('on', a.getAttribute('href') === '#' + id); });
    };
    setActive(sections[0].id);
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { if (e.isIntersecting) setActive(e.target.id); });
      }, { rootMargin: '-45% 0px -50% 0px' });
      sections.forEach(function (s) { io.observe(s); });
    }
  }
})();
