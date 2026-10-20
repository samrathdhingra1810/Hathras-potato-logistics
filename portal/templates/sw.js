// ColdFlow service worker: works on spotty connections.
// - Static assets & CDN libraries: cache-first.
// - Pages and GET API calls: network-first, falling back to the last cached copy,
//   then to the offline page.
// - POSTs (assistant, analysis, saves) always go to the network.
// Rendered by Flask: VERSION changes with every asset change, so old caches are dropped.
const VERSION = 'coldflow-{{ version }}';
const V = '?v={{ version }}';
const CORE = [
  '/', '/plan', '/hathras', '/tools/planner', '/tools/forecast', '/tools/map', '/workspace/fpo', '/offline',
  '/static/css/site.css' + V, '/static/css/home.css' + V, '/static/js/site.js' + V, '/static/js/charts.js' + V, '/static/js/assistant.js' + V,
  '/static/js/palette.js' + V, '/static/js/planner.js' + V, '/static/js/plan.js' + V, '/static/js/map.js' + V, '/static/js/workspace.js' + V,
  '/static/img/mark.svg' + V,
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(VERSION).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function isStatic(url) {
  return url.pathname.startsWith('/static/') || url.hostname === 'cdnjs.cloudflare.com';
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.hostname.endsWith('tile.openstreetmap.org')) return; // map tiles: let the browser handle them
  const sameOrigin = url.origin === self.location.origin;
  if (!sameOrigin && url.hostname !== 'cdnjs.cloudflare.com') return;
  // Account pages are personal: never serve them from cache.
  if (sameOrigin && /^\/(dashboard|account|login|signup|logout)/.test(url.pathname)) return;

  if (isStatic(url)) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        if (res.ok) caches.open(VERSION).then((c) => c.put(req, res.clone()));
        return res;
      }))
    );
    return;
  }

  event.respondWith(
    fetch(req).then((res) => {
      if (res.ok && sameOrigin) {
        const copy = res.clone();
        caches.open(VERSION).then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() => caches.match(req).then((hit) => {
      if (hit) return hit;
      if (req.mode === 'navigate') return caches.match('/offline');
      return new Response(JSON.stringify({ error: "You're offline. Reconnect to update this view." }),
        { status: 503, headers: { 'Content-Type': 'application/json' } });
    }))
  );
});
