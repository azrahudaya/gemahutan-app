/* Service worker GemaHutan.
 *
 * Aturan yang dipegang:
 * 1. Permintaan ke API tidak pernah diambil dari cache. Data deteksi, status
 *    job, dan angka dashboard harus selalu dari server, bukan dari salinan lama.
 * 2. Hanya berkas statis milik aplikasi sendiri (ikon, manifes, aset _next)
 *    yang disimpan. Permintaan lintas asal, termasuk ubin peta, dibiarkan lewat.
 * 3. Permintaan selain GET dan permintaan dengan header Authorization langsung
 *    dilewatkan tanpa disentuh.
 *
 * Naikkan VERSI setiap kali daftar aset inti berubah supaya cache lama dibuang.
 */

const VERSI = "gemahutan-v2";

const ASET_INTI = [
  "/",
  "/manifest.webmanifest",
  "/favicon.ico",
  "/icon-192.png",
  "/icon-512.png",
  "/icon-maskable-512.png",
  "/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(VERSI)
      // Satu aset gagal tidak boleh membatalkan seluruh instalasi.
      .then((cache) => Promise.allSettled(ASET_INTI.map((url) => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((nama) =>
        Promise.all(nama.filter((n) => n !== VERSI).map((n) => caches.delete(n)))
      )
      .then(() => self.clients.claim())
  );
});

function bolehDisimpan(request, url) {
  if (request.method !== "GET") return false;
  if (url.origin !== self.location.origin) return false;
  if (url.pathname.startsWith("/api/")) return false;
  if (url.pathname.startsWith("/_next/data/")) return false;
  if (request.headers.has("authorization")) return false;
  if (request.headers.get("accept")?.includes("text/event-stream")) return false;
  return true;
}

function asetStatis(pathname) {
  return (
    pathname.startsWith("/_next/static/") ||
    pathname.startsWith("/_next/image") ||
    /\.(?:png|jpe?g|svg|ico|webp|woff2?|css|js|webmanifest)$/.test(pathname)
  );
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (!bolehDisimpan(request, url)) return;

  // Navigasi: coba jaringan dulu, cache hanya dipakai kalau jaringan gagal.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res && res.ok && res.type === "basic") {
            const salinan = res.clone();
            caches.open(VERSI).then((cache) => cache.put(request, salinan));
          }
          return res;
        })
        .catch(() => caches.match(request).then((hit) => hit || caches.match("/")))
    );
    return;
  }

  if (!asetStatis(url.pathname)) return;

  // Aset statis: sajikan dari cache, perbarui di latar belakang.
  event.respondWith(
    caches.match(request).then((hit) => {
      const dariJaringan = fetch(request)
        .then((res) => {
          if (res && res.ok && res.type === "basic") {
            const salinan = res.clone();
            caches.open(VERSI).then((cache) => cache.put(request, salinan));
          }
          return res;
        })
        .catch(() => hit);
      return hit || dariJaringan;
    })
  );
});
