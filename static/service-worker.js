// Service Worker Minimalista
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
    // Apenas repassa a requisição (necessário para o PWA ser válido)
    event.respondWith(fetch(event.request));
});
