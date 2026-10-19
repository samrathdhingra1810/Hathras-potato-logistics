// ColdFlow service worker: works on spotty connections.
// - Static assets & CDN libraries: cache-first.
// - Pages and GET API calls: network-first, falling back to the last cached copy,
//   then to the offline page.
// - POSTs (assistant, analysis, saves) always go to the network.
const VERSION = 'coldflow-v1';
const CORE = [
  '/', '/plan', '/hathras', '/tools/planner', '/tools/forecast', '/tools/map', '/offline',
  '/static/css/site.css', '/static/js/site.js', '/static/js/charts.js', '/static/js/assistant.js',
  '/static/js/palette.js', '/static/js/planner.js', '/static/js/plan.js', '/static/js/map.js',
  '/static/img/mark.svg',
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
