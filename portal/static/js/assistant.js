// ColdFlow Assistant panel: chat UI over /api/assistant. History persists for the tab
// (sessionStorage) so the conversation survives page changes.
(function () {
  var panel = document.getElementById('assistant');
  if (!panel) return;
  var log = document.getElementById('assistant-log');
  var form = panel.querySelector('[data-assistant-form]');
  var input = document.getElementById('assistant-input');
  var modeEl = panel.querySelector('[data-mode]');
  var suggest = panel.querySelector('[data-suggest]');
  var fabs = document.querySelectorAll('[data-open-assistant]');
  var KEY = 'cf-assistant';
  var history = [];
  var busy = false;

  try { history = JSON.parse(sessionStorage.getItem(KEY) || '[]'); } catch (e) { history = []; }
  function persist() { try { sessionStorage.setItem(KEY, JSON.stringify(history.slice(-20))); } catch (e) { /* ignore */ } }

  // ---- Minimal, safe Markdown: escape everything, then allow bold/italic/code, lists and internal links.
  function esc(s) { return s.replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function inline(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
      .replace(/(^|\s)_([^_\n]+)_(?=\s|$|[.,])/g, '$1<em>$2</em>')
      .replace(/\[([^\]]+)\]\((\/[^)\s]*)\)/g, function (_m, text, href) {
        if (href.indexOf('//') === 0) return text; // internal paths only
        return '<a href="' + href + '" data-transition>' + text + '</a>';
      });
  }
  function md(text) {
    var out = [], list = null;
    text.split('\n').forEach(function (line) {
      var li = /^\s*(?:[-*•]|\d+\.)\s+(.*)$/.exec(line);
      if (li) {
        if (!list) { list = []; }
        list.push('<li>' + inline(li[1]) + '</li>');
        return;
      }
      if (list) { out.push('<ul>' + list.join('') + '</ul>'); list = null; }
      if (line.trim()) out.push('<p>' + inline(line) + '</p>');
    });
    if (list) out.push('<ul>' + list.join('') + '</ul>');
    return out.join('');
  }

  function bubble(role, text, extra) {
    var div = document.createElement('div');
    div.className = 'msg ' + (role === 'user' ? 'me' : 'bot') + (extra ? ' ' + extra : '');
    if (role === 'user') div.textContent = text; else div.innerHTML = md(text);
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
  }

  function renderHistory() {
    log.querySelectorAll('.msg:not(.intro)').forEach(function (n) { n.remove(); });
    history.forEach(function (m) { bubble(m.role, m.content); });
    suggest.hidden = history.length > 0;
  }

  function setMode(mode) {
    modeEl.textContent = mode === 'ai' ? 'AI · uses ColdFlow data' : mode === 'offline' ? 'Offline help' : 'Ready';
    modeEl.dataset.state = mode || '';
  }

  function pageContext() {
    var ctx = { page: location.pathname, title: document.title };
    if (typeof window.CF_getPlan === 'function') {
      try { ctx.plan = window.CF_getPlan(); } catch (e) { /* ignore */ }
    }
    return ctx;
  }

  function send(text) {
    text = (text || '').trim();
    if (!text || busy) return;
    busy = true;
    history.push({ role: 'user', content: text.slice(0, 2000) });
    persist();
    suggest.hidden = true;
    bubble('user', text);
    var typing = bubble('bot', '', 'typing');
    typing.innerHTML = '<span></span><span></span><span></span>';
    form.querySelector('button').disabled = true;

    fetch('/api/assistant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: history, context: pageContext() }),
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        typing.remove();
        var reply = res.ok ? res.body.reply : (res.body.error || 'Something went wrong. Try again.');
        if (res.ok) { history.push({ role: 'assistant', content: reply }); persist(); setMode(res.body.mode); }
        bubble('assistant', reply, res.ok ? '' : 'error');
      })
      .catch(function () {
        typing.remove();
        bubble('assistant', "I couldn't reach ColdFlow. Check your connection and try again.", 'error');
      })
      .then(function () { busy = false; form.querySelector('button').disabled = false; input.focus(); });
  }

  function open(question, autoSend) {
    panel.hidden = false;
    requestAnimationFrame(function () { panel.classList.add('open'); });
    fabs.forEach(function (f) { f.setAttribute('aria-expanded', 'true'); });
    document.body.classList.add('assistant-open');
    if (question && autoSend) send(question);
    else if (question) input.value = question;
    setTimeout(function () { input.focus(); }, 60);
  }
  function close() {
    panel.classList.remove('open');
    fabs.forEach(function (f) { f.setAttribute('aria-expanded', 'false'); });
    document.body.classList.remove('assistant-open');
    setTimeout(function () { if (!panel.classList.contains('open')) panel.hidden = true; }, 220);
  }

  fabs.forEach(function (f) { f.addEventListener('click', function () { panel.classList.contains('open') ? close() : open(); }); });
  panel.querySelector('[data-assistant-close]').addEventListener('click', close);
  panel.querySelector('[data-assistant-reset]').addEventListener('click', function () {
    history = []; persist(); renderHistory(); setMode(''); input.focus();
  });
  suggest.addEventListener('click', function (e) {
    var b = e.target.closest('[data-ask]');
    if (b) send(b.dataset.ask);
  });
  form.addEventListener('submit', function (e) { e.preventDefault(); var t = input.value; input.value = ''; autosize(); send(t); });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  function autosize() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 140) + 'px'; }
  input.addEventListener('input', autosize);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && panel.classList.contains('open') && !document.getElementById('palette').classList.contains('open')) close();
  });

  renderHistory();
  window.CFAssistant = { open: open, close: close, send: send };
  // Reopen if the user was mid-conversation before navigating.
  try { if (sessionStorage.getItem(KEY + '-open') === '1') open(); } catch (e) { /* ignore */ }
  window.addEventListener('pagehide', function () {
    try { sessionStorage.setItem(KEY + '-open', panel.classList.contains('open') ? '1' : '0'); } catch (e) { /* ignore */ }
  });
})();
