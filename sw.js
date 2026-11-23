// Modo sin conexión: guarda en la tablet lo que el juego va usando (imágenes, audios, código).

const VERSION = "abecedario-v1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((claves) => Promise.all(claves.filter((c) => c !== VERSION).map((c) => caches.delete(c))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(caches.open(VERSION).then(async (cache) => {
    const guardado = await cache.match(e.request, { ignoreSearch: true });
    if (guardado) return guardado;
    const respuesta = await fetch(e.request);
    if (respuesta.ok && respuesta.status === 200) cache.put(e.request, respuesta.clone());
    return respuesta;
  }));
});
