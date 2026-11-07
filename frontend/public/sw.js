/* SAMPURNA service worker: offline app shell; API calls are never cached (sensitive data). */
const CACHE = 'sampurna-shell-v1'
const SHELL = ['/', '/index.html', '/favicon.svg', '/manifest.webmanifest', '/icon-192.png']
self.addEventListener('install', (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))); self.skipWaiting() })
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))))
  self.clients.claim()
})
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (e.request.method !== 'GET' || url.pathname.startsWith('/api')) return
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(() => caches.match('/index.html')))
    return
  }
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
    if (res.ok && url.origin === location.origin) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)) }
    return res
  })))
})
self.addEventListener('push', (e) => {
  const data = e.data ? e.data.json() : { title: 'SAMPURNA', body: 'You have a gentle reminder.' }
  e.waitUntil(self.registration.showNotification(data.title, { body: data.body, icon: '/icon-192.png' }))
})
