const CACHE = 'astra-shell-v2'
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE)
    const response = await fetch('/', {cache:'reload'})
    if (!response.ok) throw new Error('Cannot cache ASTRA shell')
    const html = await response.clone().text()
    const assets = [...html.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map(match => match[1])
    await cache.addAll(assets)
    await cache.put('/', response)
    await self.skipWaiting()
  })())
})
self.addEventListener('activate', event => event.waitUntil((async () => {
  await caches.delete('astra-shell-v1')
  await self.clients.claim()
})()))
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url)
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return
  if (event.request.mode === 'navigate' && url.pathname === '/') {
    event.respondWith(fetch(event.request, {cache:'no-store'}).catch(() => caches.match('/')))
  } else if (url.pathname.startsWith('/assets/')) {
    event.respondWith(caches.match(event.request).then(response => response || fetch(event.request)))
  }
})

