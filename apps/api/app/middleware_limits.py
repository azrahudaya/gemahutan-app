"""Pembatas laju umum untuk seluruh endpoint API.

Kenapa middleware ASGI murni, bukan BaseHTTPMiddleware: aplikasi ini punya
endpoint SSE di `/api/v1/jobs/stream`. BaseHTTPMiddleware membungkus badan
respons, dan itu membuat respons streaming menggantung. Middleware ASGI murni
hanya memeriksa permintaan masuk dan meneruskan, jadi streaming tidak tersentuh.

Kenapa anggarannya dipisah per kelas operasi: satu angka untuk semua endpoint
selalu salah. Membaca daftar spesies itu murah dan sering, sedangkan mengunggah
audio memakan storage, CPU worker, dan waktu. Jadi baca dapat jatah lega,
tulis lebih sempit, unggah paling sempit.

Pilihan sadar: kalau Redis mati, pembatas ini MELOLOSKAN permintaan. Alasannya
beda dengan pencabutan token di `services/security.py` yang menolak saat Redis
mati. Di sana salah meloloskan berarti token yang sudah logout masih bisa
dipakai, jadi aman kalau ditolak. Di sini salah menolak berarti seluruh aplikasi
mati karena satu dependensi, dan itu kerugian yang lebih besar daripada
sementara tidak ada pembatasan.
"""
import json
import time

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

PREFIX = "gemahutan:laju:"

# Saklar tingkat modul, dipakai test untuk mematikan pembatasan. Test menjalankan
# lebih dari 200 permintaan HTTP dalam beberapa detik dari satu alamat, jadi
# kalau tidak dimatikan test akan saling memblokir sendiri dan gagal karena 429
# yang bukan bagian dari yang sedang diuji.
AKTIF = True

# Path yang tidak pernah dihitung. Pemeriksa kesehatan dipanggil terus oleh
# Docker dan Caddy, jadi membatasinya justru bisa menandai kontainer tidak sehat.
LEWATI = {"/healthz", "/readyz"}

# (batas, jendela detik) per kelas operasi.
ANGGARAN = {
    "baca": (300, 60),
    "tulis": (60, 60),
    "unggah": (20, 60),
}

# Awalan path yang dianggap unggah. Paling sempit karena paling mahal.
AWALAN_UNGGAH = ("/api/v1/recordings", "/api/v1/batches")

# Path yang punya pembatas sendiri di dalam endpoint (login sudah punya
# penguncian per email dan IP). Dibiarkan lewat supaya tidak dihitung dua kali
# dengan semantik yang berbeda.
LEWATI_PREFIX = ("/api/v1/auth/login",)


def _kelas_operasi(method: str, path: str) -> str | None:
    for awal in AWALAN_UNGGAH:
        if path.startswith(awal) and method in ("POST", "PUT", "PATCH"):
            return "unggah"
    if method in ("GET", "HEAD", "OPTIONS"):
        return "baca"
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "tulis"
    return None


def _ip_klien(scope: dict) -> str:
    """Ambil IP klien dari scope. Uvicorn --proxy-headers sudah memproses XFF.

    Jangan baca header X-Forwarded-For mentah dari scope -- uvicorn sudah
    memperbarui scope['client'] dengan IP tepercaya. Membaca header mentah
    berarti pembatas laju bisa dilewati dengan X-Forwarded-For palsu."""
    klien = scope.get("client")
    return klien[0] if klien else "tanpa-ip"


class PembatasLaju:
    """Middleware ASGI: hitung permintaan per IP dan kelas operasi di Redis."""

    def __init__(self, app, aktif: bool = True) -> None:
        self.app = app
        self.aktif = aktif
        self._klien: aioredis.Redis | None = None

    def _redis(self) -> aioredis.Redis:
        # Satu koneksi dipakai ulang. Membuat koneksi baru tiap permintaan
        # menambah latensi dan menghabiskan soket.
        if self._klien is None:
            self._klien = aioredis.from_url(settings.redis_url, decode_responses=True)
        return self._klien

    async def _hitung(self, kunci: str, batas: int, jendela: int) -> tuple[bool, int]:
        """Kembalikan (boleh, sisa_detik). Gagal Redis berarti boleh."""
        try:
            klien = self._redis()
            jumlah = await klien.incr(kunci)
            if jumlah == 1:
                await klien.expire(kunci, jendela)
            if jumlah > batas:
                ttl = await klien.ttl(kunci)
                return False, max(1, int(ttl))
            return True, 0
        except Exception:  # noqa: BLE001 - Redis mati = meloloskan, lihat docstring modul
            return True, 0

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not (self.aktif and AKTIF):
            return await self.app(scope, receive, send)

        path = scope.get("path", "")
        if path in LEWATI or path.startswith(LEWATI_PREFIX):
            return await self.app(scope, receive, send)

        kelas = _kelas_operasi(scope.get("method", "GET"), path)
        if kelas is None:
            return await self.app(scope, receive, send)

        batas, jendela = ANGGARAN[kelas]
        ip = _ip_klien(scope)
        # Jendela tetap: kunci berganti tiap jendela, jadi tidak perlu simpan
        # riwayat waktu tiap permintaan.
        kunci = f"{PREFIX}{kelas}:{ip}:{int(time.time() // jendela)}"
        boleh, sisa = await self._hitung(kunci, batas, jendela)
        if boleh:
            return await self.app(scope, receive, send)

        badan = json.dumps(
            {
                "detail": (
                    f"Terlalu banyak permintaan. Batas {batas} per {jendela} detik "
                    f"untuk operasi {kelas}. Coba lagi dalam {sisa} detik."
                ),
                "kelas": kelas,
                "batas": batas,
                "jendela_detik": jendela,
            }
        ).encode()

        kepala = [
            (b"content-type", b"application/json"),
            (b"retry-after", str(sisa).encode()),
            (b"content-length", str(len(badan)).encode()),
        ]
        # Header CORS harus ikut, kalau tidak browser melaporkan galat CORS yang
        # menyesatkan padahal sebenarnya kena pembatasan laju.
        asal = ""
        for nama, nilai in scope.get("headers") or []:
            if nama == b"origin":
                asal = nilai.decode("latin-1")
                break
        if asal:
            kepala.append((b"access-control-allow-origin", asal.encode()))
            kepala.append((b"access-control-allow-credentials", b"true"))
            kepala.append((b"vary", b"Origin"))

        await send({"type": "http.response.start", "status": 429, "headers": kepala})
        await send({"type": "http.response.body", "body": badan})
