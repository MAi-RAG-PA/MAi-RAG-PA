// frontend/public/sw.js
// Self-destructing service worker.
// Any previously-installed SW will be replaced by this one, which
// unregisters itself and clears all caches, then stops intercepting
// any network requests. Do NOT re-add fetch handlers here.

self.addEventListener('install', (event) => {
  console.log('[SW] Self-destruct: installing');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('[SW] Self-destruct: activating, clearing caches');
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.map((n) => caches.delete(n))))
      .then(() => self.registration.unregister())
      .then(() => self.clients.matchAll())
      .then((clients) => clients.forEach((c) => c.navigate(c.url)))
  );
});

// No fetch handler — that's the point.
