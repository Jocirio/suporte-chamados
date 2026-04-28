self.addEventListener('install', (e) => {
  console.log('Service Worker instalado!');
});

self.addEventListener('fetch', (e) => {
  // Aqui você controlaria o cache offline no futuro
  e.respondWith(fetch(e.request));
});
