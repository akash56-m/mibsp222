const CACHE_NAME = 'mibsp-v1';
const PRECACHE_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/favicon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .catch(() => Promise.resolve())
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const cacheKeys = await caches.keys();
    await Promise.all(
      cacheKeys
        .filter((key) => key !== CACHE_NAME)
        .map((key) => caches.delete(key))
    );
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET' || request.url.startsWith('http') === false) {
    return;
  }

  const isSameOrigin = new URL(request.url).origin === self.location.origin;
  if (!isSameOrigin) {
    return;
  }

  const isStaticAsset = request.url.includes('/static/');
  const isHealthOrApi = request.url.includes('/api/');

  if (isHealthOrApi) {
    event.respondWith(fetch(request));
    return;
  }

  if (isStaticAsset) {
    event.respondWith(
      caches.match(request)
        .then((cached) => cached || fetch(request))
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (!response || response.status !== 200) {
          throw new Error('Network response not cached');
        }
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        return response;
      })
      .catch(() => caches.match('/'))
  );
});
