/* BHUSHAKTI AI service worker.
   - App shell cached for offline start.
   - Read-only operational GETs use network-first with a cached fallback.
   - Writes are never cached or replayed here: the field report queue in IndexedDB
     owns retries and only marks a report synced after the server acknowledges it. */

const VERSION = "bhushakti-v1";
const SHELL = ["/", "/index.html", "/manifest.webmanifest", "/icon.svg"];
const CACHEABLE_API = [/^\/api\/v1\/risk\/summary/, /^\/api\/v1\/risk-zones/, /^\/api\/v1\/public\//, /^\/api\/v1\/health/];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith("/api/")) {
    if (!CACHEABLE_API.some((pattern) => pattern.test(url.pathname))) return;
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(VERSION).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(async () => {
          const cached = await caches.match(request);
          if (cached) return cached;
          return new Response(JSON.stringify({ error: { code: "offline", message: "Offline and no cached snapshot is available." } }), {
            status: 503,
            headers: { "Content-Type": "application/json" },
          });
        }),
    );
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(VERSION).then((cache) => cache.put("/index.html", clone));
          return response;
        })
        .catch(() => caches.match("/index.html")),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => cached ?? fetch(request).then((response) => {
      if (response.ok && /\.(js|css|woff2?|svg|png)$/.test(url.pathname)) {
        const clone = response.clone();
        caches.open(VERSION).then((cache) => cache.put(request, clone));
      }
      return response;
    })),
  );
});
