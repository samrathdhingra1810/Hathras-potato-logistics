// Voice accessibility: read status cards aloud (speechSynthesis) and pick a block by voice
// (SpeechRecognition). Uses only browser APIs; controls stay hidden where unsupported.
(function () {
  var CF = window.CF || {};
  function lang() { return CF.lang ? CF.lang() : 'en'; }
  var HI = function () { return lang() === 'hi'; };

  // ---------- Block matching (shared by the map filter and the microphone) ----------
  function norm(s) {
    return String(s || '').toLowerCase().normalize('NFC').replace(/[.,!?।"'()\-]/g, ' ').replace(/\s+/g, ' ').trim();
  }
  function lev(a, b) {
    var m = a.length, n = b.length, d = [], i, j;
    for (i = 0; i <= m; i++) d[i] = [i];
    for (j = 0; j <= n; j++) d[0][j] = j;
    for (i = 1; i <= m; i++) for (j = 1; j <= n; j++) {
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    }
    return d[m][n];
  }
  /** Best block for a spoken or typed phrase, e.g. "storage in Sadabad" or "सादाबाद में जगह". */
  function matchBlock(text) {
    var t = norm(text);
    if (!t) return null;
    var words = t.split(' '), cands = [];
    words.forEach(function (w, i) { cands.push(w); if (words[i + 1]) cands.push(w + ' ' + words[i + 1]); });
    var best = null;
    (CF.blocks || []).forEach(function (b) {
      [b.name, b.hi].concat(b.aliases || []).map(norm).forEach(function (n) {
        if (!n) return;
        var score = (' ' + t + ' ').indexOf(' ' + n + ' ') >= 0 ? 0 : null;
        if (score === null) cands.forEach(function (c) {
          if (c.length < 3) return;
          var rel = lev(c, n) / Math.max(n.length, c.length);
          if (rel <= 0.34 && (score === null || rel < score)) score = rel;
        });
        if (score !== null && (!best || score < best.score)) best = { block: b, score: score };
      });
    });
    return best ? best.block : null;
  }
  window.CFVoice = { matchBlock: matchBlock };

  // ---------- Small announcement area ----------
  function statusFor(el) {
    var box = el && el.closest('.fv-tile, .block-filter, .card-body, section');
    return (box && box.querySelector('[data-voice-status]')) || null;
  }
  var toastTimer;
  function announce(el, text) {
    var s = statusFor(el);
    if (!s) {
      s = document.getElementById('voice-toast');
      if (!s) { s = document.createElement('p'); s.id = 'voice-toast'; s.className = 'voice-toast'; s.setAttribute('aria-live', 'polite'); document.body.appendChild(s); }
      clearTimeout(toastTimer); toastTimer = setTimeout(function () { s.hidden = true; }, 5000);
    }
    s.textContent = text; s.hidden = false;
  }

  // ---------- Read aloud ----------
  var synth = window.speechSynthesis;
  if (synth && window.SpeechSynthesisUtterance) {
    document.querySelectorAll('[data-say]').forEach(function (b) { b.hidden = false; });
    var speaking = null;
    var voices = [];
    var loadVoices = function () { voices = synth.getVoices() || []; };
    loadVoices();
    if ('onvoiceschanged' in synth) synth.addEventListener('voiceschanged', loadVoices);
    var voiceFor = function (code) {
      return voices.filter(function (v) { return v.lang && v.lang.toLowerCase().replace('_', '-').indexOf(code) === 0; })[0] || null;
    };
    var reset = function () {
      if (speaking) { speaking.setAttribute('aria-pressed', 'false'); speaking.classList.remove('is-speaking'); }
      speaking = null;
    };
    document.addEventListener('click', function (e) {
      var b = e.target.closest('[data-say]');
      if (!b) return;
      var again = speaking === b;
      synth.cancel(); reset();
      if (again) return;                                   // second tap stops
      var hi = HI(), text = hi ? b.dataset.sayHi : b.dataset.sayEn, code = hi ? 'hi' : 'en';
      var v = voiceFor(hi ? 'hi' : 'en-in') || (hi ? null : voiceFor('en'));
      if (hi && !v && voices.length) {
        // No Hindi voice installed: read the English text rather than mispronounce Hindi.
        text = b.dataset.sayEn; code = 'en'; v = voiceFor('en-in') || voiceFor('en');
        announce(b, 'इस डिवाइस पर हिंदी आवाज़ नहीं मिली, इसलिए अंग्रेज़ी में सुना रहे हैं। फ़ोन की सेटिंग में हिंदी आवाज़ जोड़ सकते हैं।');
      }
      var u = new SpeechSynthesisUtterance(text);
      u.lang = code === 'hi' ? 'hi-IN' : 'en-IN';
      if (v) u.voice = v;
      u.rate = 0.95;
      u.onend = u.onerror = function () { if (speaking === b) reset(); };
      speaking = b; b.setAttribute('aria-pressed', 'true'); b.classList.add('is-speaking');
      synth.speak(u);
    });
    document.addEventListener('cf:lang', function () { synth.cancel(); reset(); });
  }

  // ---------- Pick a block by voice ----------
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR) {
    document.querySelectorAll('[data-voice-target]').forEach(function (b) { b.hidden = false; });
    document.querySelectorAll('[data-voice-note]').forEach(function (n) { n.hidden = false; });
    var rec = null, recBtn = null;
    var stop = function () {
      if (recBtn) { recBtn.setAttribute('aria-pressed', 'false'); recBtn.classList.remove('is-listening'); }
      recBtn = null; rec = null;
    };
    var fill = function (target, block, heard) {
      if (target.tagName === 'SELECT') {
        if (!block) return false;
        target.value = block.id;
        target.dispatchEvent(new Event('change', { bubbles: true }));
      } else {
        target.value = block ? (HI() ? block.hi : block.name) : heard;
        target.dispatchEvent(new Event('input', { bubbles: true }));
      }
      return true;
    };
    document.addEventListener('click', function (e) {
      var b = e.target.closest('[data-voice-target]');
      if (!b) return;
      if (rec) { rec.abort(); stop(); return; }           // second tap cancels
      var target = document.querySelector(b.dataset.voiceTarget);
      if (!target) return;
      rec = new SR(); recBtn = b;
      rec.lang = HI() ? 'hi-IN' : 'en-IN';
      rec.interimResults = false;
      rec.maxAlternatives = 5;
      b.setAttribute('aria-pressed', 'true'); b.classList.add('is-listening');
      announce(b, HI() ? 'सुन रहे हैं… ब्लॉक का नाम बोलें, जैसे "सादाबाद"।' : 'Listening… say a block name, like "Sadabad".');
      rec.onresult = function (ev) {
        var alts = Array.prototype.map.call(ev.results[0], function (a) { return a.transcript; });
        var block = null;
        for (var i = 0; i < alts.length && !block; i++) block = matchBlock(alts[i]);
        var heard = alts[0] || '';
        if (fill(target, block, heard) && block) {
          announce(b, HI() ? 'सुना: "' + heard + '" → ' + block.hi : 'Heard "' + heard + '" → ' + block.name);
        } else {
          announce(b, HI() ? 'सुना: "' + heard + '", पर कोई ब्लॉक नहीं मिला। फिर से बोलें या सूची से चुनें।'
                           : 'Heard "' + heard + '" but no block matched. Try again or pick from the list.');
        }
      };
      rec.onerror = function (ev) {
        var msg = {
          'not-allowed': HI() ? 'माइक्रोफ़ोन की अनुमति बंद है। ब्राउज़र सेटिंग में अनुमति दें।' : 'Microphone access is blocked. Allow it in your browser settings.',
          'service-not-allowed': HI() ? 'इस ब्राउज़र में आवाज़ से खोज उपलब्ध नहीं है।' : 'Voice input is not available in this browser.',
          'no-speech': HI() ? 'कुछ सुनाई नहीं दिया। फिर से कोशिश करें।' : "Didn't hear anything. Try again.",
          'network': HI() ? 'आवाज़ पहचान के लिए इंटरनेट चाहिए।' : 'Voice recognition needs an internet connection.',
          'audio-capture': HI() ? 'कोई माइक्रोफ़ोन नहीं मिला।' : 'No microphone was found.',
        }[ev.error];
        if (msg) announce(b, msg);
      };
      rec.onend = stop;
      try { rec.start(); } catch (err) { stop(); }
    });
  }
})();
