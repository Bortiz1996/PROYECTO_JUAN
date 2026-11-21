const CACHE_NAME = "juan-pwa-v1";
const PRECACHE_URLS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./assets/juan_icon.png",
  "./assets/juan_portada.webp",
  "./static/apple-touch-icon.png",
  "./static/juan_icon_192.png",
  "./static/juan_icon_512.png",
  "./static/juan_icon_maskable_512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      Promise.allSettled(
        PRECACHE_URLS.map((url) =>
          cache.add(new Request(url, { cache: "reload" }))
        )
      )
    )
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((oldKey) => caches.delete(oldKey))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  const isNavigation = request.mode === "navigate";
  const isDynamicData =
    url.pathname.includes("/api/") ||
    url.pathname.endsWith("/fews_calamar.json") ||
    url.pathname.endsWith("/nivel_calamar.csv");

  if (isNavigation || isDynamicData) {
    event.respondWith(networkFirst(request, isNavigation));
    return;
  }

  event.respondWith(staleWhileRevalidate(request));
});

async function networkFirst(request, isNavigation) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const response = await fetch(request);
    if (response && response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    if (isNavigation) {
      const shell =
        (await cache.match("./index.html")) || (await cache.match("./"));
      if (shell) return shell;
    }
    return new Response("Sin conexión", {
      status: 503,
      statusText: "Service Unavailable",
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const networkPromise = fetch(request)
    .then((response) => {
      if (response && response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => null);

  if (cached) {
    return cached;
  }
  const networkResponse = await networkPromise;
  return (
    networkResponse ||
    new Response("", { status: 504, statusText: "Gateway Timeout" })
  );
}
