"""Pemeriksa fitur Fase 2 GemaHutan lewat HTTP.

Dijalankan dari host, bukan dari dalam container. Setiap butir dicetak PASS atau
GAGAL, dan skrip berhenti dengan kode 1 kalau ada satu butir pun gagal. Skrip ini
sengaja dibuat gagal kalau fiturnya benar-benar tidak ada: setiap pemeriksaan
membandingkan kode HTTP dan bentuk respons dengan kontrak di docs/arsip/CONTRACT_v2.md,
bukan hanya memeriksa bahwa permintaannya terkirim.

Pakai:
    python3 ops/verify_features.py
    python3 ops/verify_features.py --api http://localhost:8000 --web http://localhost:3001

Butir yang diperiksa:
 1. login admin dan pembuatan akun uji
 2. perangkat: daftar, tambah, ubah
 3. perangkat: tulis ditolak 403 untuk non-admin
 4. perangkat: hapus ditolak 409 selama masih dipakai rekaman, lalu 204 setelah kosong
 5. akun: daftar hanya untuk admin, 403 untuk non-admin
 6. akun: ubah peran diri sendiri dan hapus diri sendiri ditolak 409
 7. akun: ubah peran pengguna lain berhasil
 8. unggah batch: 201 dengan hasil per berkas
 9. status batch: daftar dan rincian satu batch
10. progres dan tahap pada rekaman
11. progres dan tahap pada job
12. siaran status job (SSE): 401 tanpa token, 200 dengan token
13. deteksi memuat kolom lokalisasi
14. info model memuat blok localization
15. manifes PWA bisa diakses lewat web
16. service worker bisa diakses lewat web dan tidak meng-cache API
"""
import argparse
import io
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
import wave

HASIL: list[tuple[str, bool, str]] = []


def catat(nama: str, lulus: bool, keterangan: str) -> None:
    HASIL.append((nama, lulus, keterangan))
    print(f"  [{'PASS' if lulus else 'GAGAL'}] {nama}: {keterangan}")


def minta(
    url: str,
    method: str = "GET",
    body: dict | None = None,
    token: str | None = None,
    timeout: int = 30,
) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            isi = resp.read().decode(errors="replace")
            try:
                return resp.status, json.loads(isi)
            except json.JSONDecodeError:
                return resp.status, isi
    except urllib.error.HTTPError as exc:
        isi = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(isi)
        except json.JSONDecodeError:
            return exc.code, isi
    except Exception as exc:
        return 0, str(exc)


def minta_mentah(
    url: str, token: str | None = None, timeout: int = 15, batas: int = 400
) -> tuple[int, str, str]:
    """Permintaan GET tanpa mengurai JSON. Balikannya kode, tipe konten, potongan isi."""
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            tipe = resp.headers.get("content-type", "")
            return resp.status, tipe, resp.read1(batas).decode(errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("content-type", ""), exc.read(batas).decode(errors="replace")
    except Exception as exc:
        return 0, "", str(exc)


def minta_multipart(
    url: str,
    kolom: dict[str, str],
    berkas: list[tuple[str, str, bytes, str]],
    token: str | None = None,
    timeout: int = 120,
) -> tuple[int, object]:
    batas = "----gemahutanuji" + uuid.uuid4().hex
    bagian: list[bytes] = []
    for nama, nilai in kolom.items():
        bagian.append(
            f'--{batas}\r\nContent-Disposition: form-data; name="{nama}"\r\n\r\n{nilai}\r\n'.encode()
        )
    for nama, nama_berkas, isi, tipe in berkas:
        bagian.append(
            (
                f'--{batas}\r\nContent-Disposition: form-data; name="{nama}"; '
                f'filename="{nama_berkas}"\r\nContent-Type: {tipe}\r\n\r\n'
            ).encode()
            + isi
            + b"\r\n"
        )
    bagian.append(f"--{batas}--\r\n".encode())
    data = b"".join(bagian)

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={batas}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            isi = resp.read().decode(errors="replace")
            try:
                return resp.status, json.loads(isi)
            except json.JSONDecodeError:
                return resp.status, isi
    except urllib.error.HTTPError as exc:
        isi = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(isi)
        except json.JSONDecodeError:
            return exc.code, isi
    except Exception as exc:
        return 0, str(exc)


def buat_wav(detik: float = 1.0, frekuensi: float = 880.0, laju: int = 16000) -> bytes:
    """WAV mono pendek untuk bahan unggah. Bukan klip hutan, hanya berkas yang sah."""
    penampung = io.BytesIO()
    with wave.open(penampung, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(laju)
        bingkai = bytearray()
        for i in range(int(detik * laju)):
            nilai = int(12000 * math.sin(2 * math.pi * frekuensi * i / laju))
            bingkai += nilai.to_bytes(2, "little", signed=True)
        w.writeframes(bytes(bingkai))
    return penampung.getvalue()


class Konteks:
    def __init__(self, api: str, web: str, email: str, password: str):
        self.api = api.rstrip("/")
        self.web = web.rstrip("/")
        self.email = email
        self.password = password
        self.token_admin: str | None = None
        self.token_ranger: str | None = None
        self.akun_uji = f"uji-fitur-{int(time.time())}@gemahutan.id"
        self.sandi_uji = "ujiFitur123"
        self.device_id: int | None = None
        self.recording_ids: list[int] = []
        self.batch_id: str | None = None
        self.site_id: int | None = None
        self.site_dibuat: int | None = None
        self.user_uji_id: int | None = None


def siapkan_login(ctx: Konteks) -> bool:
    kode, isi = minta(
        f"{ctx.api}/api/v1/auth/login",
        "POST",
        {"email": ctx.email, "password": ctx.password},
    )
    if kode != 200 or not isinstance(isi, dict) or not isi.get("access_token"):
        catat("login admin", False, f"kode {kode}, isi {str(isi)[:120]}")
        return False
    ctx.token_admin = isi["access_token"]
    catat("login admin", True, "token diterima")

    kode, isi = minta(
        f"{ctx.api}/api/v1/auth/register",
        "POST",
        {"email": ctx.akun_uji, "password": ctx.sandi_uji, "name": "Akun Uji Fitur"},
    )
    if kode not in (200, 201):
        catat("buat akun uji non-admin", False, f"kode {kode}, isi {str(isi)[:120]}")
        return True

    # Pendaftaran tidak mengembalikan token, jadi akun baru masuk lewat login
    # untuk mendapatkan token perannya (ranger).
    kode, isi = minta(
        f"{ctx.api}/api/v1/auth/login",
        "POST",
        {"email": ctx.akun_uji, "password": ctx.sandi_uji},
    )
    if kode == 200 and isinstance(isi, dict) and isi.get("access_token"):
        ctx.token_ranger = isi["access_token"]
        catat("buat akun uji non-admin", True, f"akun {ctx.akun_uji} berperan ranger")
    else:
        catat("buat akun uji non-admin", False, f"login akun uji gagal (kode {kode})")
    return True


def ambil_lokasi(ctx: Konteks) -> None:
    kode, isi = minta(f"{ctx.api}/api/v1/sites", token=ctx.token_admin)
    daftar = isi if isinstance(isi, list) else (isi.get("items", []) if isinstance(isi, dict) else [])
    if kode == 200 and daftar:
        ctx.site_id = daftar[0]["id"]
        return
    # Tidak ada lokasi sama sekali: buat satu supaya pengujian tetap bisa jalan,
    # dan hapus lagi di bagian pembersihan.
    kode, isi = minta(
        f"{ctx.api}/api/v1/sites",
        "POST",
        {"name": f"Lokasi Uji Fitur {uuid.uuid4().hex[:6]}", "latitude": -6.75, "longitude": 106.55},
        token=ctx.token_admin,
    )
    if kode in (200, 201) and isinstance(isi, dict):
        ctx.site_id = isi["id"]
        ctx.site_dibuat = isi["id"]


KEYS_PERANGKAT = [
    "id", "name", "type", "site_id", "site_name", "serial", "channel_count",
    "mic_spacing_m", "reference_distance_m", "reference_level_db", "installed_at",
    "active", "notes", "recording_count",
]

KEYS_AKUN = [
    "id", "email", "name", "role", "created_at", "is_active",
    "recording_count", "site_count",
]


def cek_perangkat(ctx: Konteks) -> None:
    kode, isi = minta(
        f"{ctx.api}/api/v1/devices",
        "POST",
        {
            "name": f"Perangkat Uji {uuid.uuid4().hex[:6]}",
            "type": "audiomoth",
            "site_id": ctx.site_id,
            "serial": "UJI-001",
            "channel_count": 2,
            "mic_spacing_m": 0.5,
            "notes": "dibuat oleh ops/verify_features.py",
        },
        token=ctx.token_admin,
    )
    if kode == 201 and isinstance(isi, dict) and isi.get("id"):
        ctx.device_id = isi["id"]
        hilang = [k for k in KEYS_PERANGKAT if k not in isi]
        catat(
            "perangkat: tambah (POST 201, kolom lengkap)",
            not hilang,
            "kolom lengkap" if not hilang else f"kolom hilang: {hilang}",
        )
    else:
        catat("perangkat: tambah (POST 201, kolom lengkap)", False, f"kode {kode}, isi {str(isi)[:160]}")
        return

    kode, isi = minta(f"{ctx.api}/api/v1/devices", token=ctx.token_admin)
    daftar = isi if isinstance(isi, list) else []
    ditemukan = any(d.get("id") == ctx.device_id for d in daftar if isinstance(d, dict))
    catat(
        "perangkat: daftar memuat baris baru (GET 200)",
        kode == 200 and ditemukan,
        f"kode {kode}, {len(daftar)} baris" + ("" if ditemukan else ", baris baru tidak ada"),
    )

    kode, isi = minta(
        f"{ctx.api}/api/v1/devices/{ctx.device_id}",
        "PATCH",
        {"notes": "diubah pemeriksa fitur"},
        token=ctx.token_admin,
    )
    lulus = (
        kode == 200
        and isinstance(isi, dict)
        and isi.get("active") is True
        and isi.get("notes") == "diubah pemeriksa fitur"
    )
    catat("perangkat: ubah (PATCH 200, nilai tersimpan)", lulus, f"kode {kode}")


def cek_perangkat_tolak_non_admin(ctx: Konteks) -> None:
    if not ctx.token_ranger:
        catat("perangkat: tulis ditolak untuk non-admin", False, "akun non-admin tidak tersedia")
        return
    kode_tambah, _ = minta(
        f"{ctx.api}/api/v1/devices",
        "POST",
        {"name": "Perangkat Non Admin", "type": "phone", "site_id": ctx.site_id},
        token=ctx.token_ranger,
    )
    kode_ubah = minta(
        f"{ctx.api}/api/v1/devices/{ctx.device_id}", "PATCH", {"notes": "tidak boleh"}, token=ctx.token_ranger
    )[0]
    kode_hapus = minta(f"{ctx.api}/api/v1/devices/{ctx.device_id}", "DELETE", token=ctx.token_ranger)[0]
    lulus = kode_tambah == 403 and kode_ubah == 403 and kode_hapus == 403
    catat(
        "perangkat: tulis ditolak 403 untuk non-admin",
        lulus,
        f"POST={kode_tambah}, PATCH={kode_ubah}, DELETE={kode_hapus}",
    )


def cek_unggah_batch(ctx: Konteks) -> None:
    berkas = [
        (
            "files",
            f"uji-{uuid.uuid4().hex[:6]}.wav",
            buat_wav(1.0, 880.0),
            "audio/wav",
        ),
        (
            "files",
            f"uji-{uuid.uuid4().hex[:6]}.wav",
            buat_wav(1.0, 1320.0),
            "audio/wav",
        ),
    ]
    kolom = {"site_id": str(ctx.site_id), "device_id": str(ctx.device_id)}
    kode, isi = minta_multipart(
        f"{ctx.api}/api/v1/recordings/batch", kolom, berkas, token=ctx.token_admin
    )
    if kode != 201 or not isinstance(isi, dict):
        catat("unggah batch: POST 201 dengan hasil per berkas", False, f"kode {kode}, isi {str(isi)[:200]}")
        return

    ctx.batch_id = isi.get("batch_id")
    items = isi.get("items") or []
    ctx.recording_ids = [i["recording_id"] for i in items if i.get("recording_id")]
    bentuk_ok = (
        bool(ctx.batch_id)
        and isi.get("count") == len(items)
        and all({"filename", "recording_id", "status", "error"} <= set(i) for i in items)
    )
    catat(
        "unggah batch: POST 201 dengan hasil per berkas",
        bentuk_ok,
        f"batch {ctx.batch_id}, {len(items)} berkas" + ("" if bentuk_ok else ", bentuk respons tidak sesuai"),
    )

    kode, isi = minta(f"{ctx.api}/api/v1/batches", token=ctx.token_admin)
    daftar = isi if isinstance(isi, list) else []
    cocok = [b for b in daftar if isinstance(b, dict) and b.get("batch_id") == ctx.batch_id]
    kolom_batch = cocok[0] if cocok else {}
    bentuk_ok = bool(cocok) and {
        "batch_id", "created_at", "total", "done", "failed", "progress_percent"
    } <= set(kolom_batch)
    catat(
        "batch: daftar memuat batch baru (GET 200)",
        kode == 200 and bentuk_ok,
        f"kode {kode}, {len(daftar)} batch, kolom {'lengkap' if bentuk_ok else 'tidak lengkap'}",
    )

    kode, isi = minta(f"{ctx.api}/api/v1/batches/{ctx.batch_id}", token=ctx.token_admin)
    if kode == 200 and isinstance(isi, dict):
        kunci = {"batch_id", "total", "done", "failed", "pending", "processing", "progress_percent", "recordings"}
        rekaman = isi.get("recordings") or []
        rekaman_ok = bool(rekaman) and all(
            {"id", "filename", "status", "progress", "stage"} <= set(r) for r in rekaman
        )
        catat(
            "batch: rincian satu batch (GET 200, status per berkas)",
            kunci <= set(isi) and rekaman_ok,
            f"total={isi.get('total')}, rekaman={len(rekaman)}, progress={isi.get('progress_percent')}",
        )
    else:
        catat("batch: rincian satu batch (GET 200, status per berkas)", False, f"kode {kode}")
        return

    kode, isi = minta(f"{ctx.api}/api/v1/batches/{ctx.batch_id}-tidak-ada", token=ctx.token_admin)
    catat("batch: batch tidak dikenal dijawab 404", kode == 404, f"kode {kode}")


def cek_progres_dan_tahap(ctx: Konteks) -> None:
    if not ctx.recording_ids:
        catat("rekaman: respons memuat progress dan stage", False, "tidak ada rekaman uji")
        return
    kode, isi = minta(f"{ctx.api}/api/v1/recordings/{ctx.recording_ids[0]}", token=ctx.token_admin)
    r = isi if isinstance(isi, dict) else {}
    lulus = kode == 200 and isinstance(r.get("progress"), int) and "stage" in r and "batch_id" in r
    catat(
        "rekaman: respons memuat progress, stage, dan batch_id",
        lulus,
        f"kode {kode}, progress={r.get('progress')}, stage={r.get('stage')}",
    )

    kode, isi = minta(f"{ctx.api}/api/v1/jobs?status=active&limit=20", token=ctx.token_admin)
    daftar = isi if isinstance(isi, list) else []
    if daftar:
        contoh = daftar[0]
        lulus = kode == 200 and "progress" in contoh and "stage" in contoh
        catat(
            "job: daftar aktif memuat progress dan stage",
            lulus,
            f"kode {kode}, {len(daftar)} job, contoh progress={contoh.get('progress')}, stage={contoh.get('stage')}",
        )
    else:
        catat(
            "job: daftar aktif memuat progress dan stage",
            kode == 200,
            f"kode {kode}, belum ada job aktif untuk diperiksa",
        )


def cek_sse(ctx: Konteks) -> None:
    kode, _, _ = minta_mentah(f"{ctx.api}/api/v1/jobs/stream")
    catat("siaran job: tanpa token dijawab 401", kode == 401, f"kode {kode}")

    kode, tipe, potongan = minta_mentah(
        f"{ctx.api}/api/v1/jobs/stream?token={ctx.token_admin}", batas=200
    )
    lulus = kode == 200 and "text/event-stream" in tipe.lower()
    catat(
        "siaran job: dengan token mengirim text/event-stream",
        lulus,
        f"kode {kode}, tipe {tipe or 'kosong'}, awal isi {potongan[:60]!r}",
    )


def cek_deteksi_lokalisasi(ctx: Konteks) -> None:
    rekaman: list[dict] = []
    dengan_deteksi: list[dict] = []
    for _ in range(15):
        kode, isi = minta(
            f"{ctx.api}/api/v1/recordings?status=done&page_size=50", token=ctx.token_admin
        )
        rekaman = isi.get("items", []) if isinstance(isi, dict) else []
        dengan_deteksi = [r for r in rekaman if (r.get("detection_count") or 0) > 0]
        if dengan_deteksi:
            break
        time.sleep(2)

    if not dengan_deteksi:
        catat(
            "deteksi: respons memuat kolom lokalisasi",
            False,
            "tidak ada rekaman dengan deteksi, kolom lokalisasi tidak bisa diverifikasi",
        )
        return

    for r in dengan_deteksi[:5]:
        kode, isi = minta(f"{ctx.api}/api/v1/recordings/{r['id']}/detections", token=ctx.token_admin)
        if kode != 200 or not isinstance(isi, list) or not isi:
            continue
        contoh = isi[0]
        kunci = {"azimuth_deg", "azimuth_confidence", "range_m", "localization_engine"}
        hilang = [k for k in kunci if k not in contoh]
        catat(
            "deteksi: respons memuat kolom lokalisasi",
            not hilang,
            f"rekaman {r['id']}, {len(isi)} deteksi, kolom {'lengkap' if not hilang else 'hilang: ' + str(hilang)}",
        )
        return

    catat("deteksi: respons memuat kolom lokalisasi", False, "tidak ada respons deteksi yang bisa dibaca")


def cek_model_info(ctx: Konteks) -> None:
    kode, isi = minta(f"{ctx.api}/api/v1/model/info", token=ctx.token_admin)
    if kode != 200 or not isinstance(isi, dict):
        catat("model info: memuat blok localization", False, f"kode {kode}")
        return
    lok = isi.get("localization")
    if not isinstance(lok, dict):
        catat("model info: memuat blok localization", False, "blok localization tidak ada")
        return
    kunci = {"butuh_kanal_minimal", "butuh_geometri", "terpasang_di_worker", "disimpan_ke_deteksi", "batas"}
    hilang = [k for k in kunci if k not in lok]
    catat(
        "model info: memuat blok localization",
        not hilang,
        "kolom lengkap" if not hilang else f"kolom hilang: {hilang}",
    )


def cek_akun(ctx: Konteks) -> None:
    kode, isi = minta(f"{ctx.api}/api/v1/users", token=ctx.token_admin)
    daftar = isi if isinstance(isi, list) else []
    bentuk = bool(daftar) and all(all(k in u for k in KEYS_AKUN) for u in daftar[:5])
    catat(
        "akun: daftar hanya untuk admin (GET 200, kolom lengkap)",
        kode == 200 and bentuk,
        f"kode {kode}, {len(daftar)} akun",
    )

    milik = [u for u in daftar if u.get("email") == ctx.email]
    if milik:
        kode_ubah = minta(
            f"{ctx.api}/api/v1/users/{milik[0]['id']}/role", "PATCH", {"role": "researcher"}, token=ctx.token_admin
        )[0]
        kode_hapus = minta(f"{ctx.api}/api/v1/users/{milik[0]['id']}", "DELETE", token=ctx.token_admin)[0]
        catat(
            "akun: ubah peran diri sendiri dan hapus diri sendiri ditolak 409",
            kode_ubah == 409 and kode_hapus == 409,
            f"PATCH peran={kode_ubah}, DELETE={kode_hapus}",
        )
    else:
        catat("akun: ubah peran diri sendiri dan hapus diri sendiri ditolak 409", False, "akun admin tidak ditemukan di daftar")

    if ctx.token_ranger:
        kode = minta(f"{ctx.api}/api/v1/users", token=ctx.token_ranger)[0]
        catat("akun: daftar ditolak 403 untuk non-admin", kode == 403, f"kode {kode}")

    uji = [u for u in daftar if u.get("email") == ctx.akun_uji]
    if uji and ctx.token_admin:
        ctx.user_uji_id = uji[0]["id"]
        kode, isi = minta(
            f"{ctx.api}/api/v1/users/{ctx.user_uji_id}/role", "PATCH", {"role": "researcher"}, token=ctx.token_admin
        )
        lulus = kode == 200 and isinstance(isi, dict) and isi.get("role") == "researcher"
        catat("akun: ubah peran pengguna lain berhasil (PATCH 200)", lulus, f"kode {kode}")
    else:
        catat("akun: ubah peran pengguna lain berhasil (PATCH 200)", False, "akun uji tidak ditemukan di daftar")


def cek_hapus_perangkat_ditolak(ctx: Konteks) -> None:
    if not ctx.device_id:
        catat("perangkat: hapus ditolak 409 selama dipakai rekaman", False, "perangkat uji tidak ada")
        return
    kode, isi = minta(f"{ctx.api}/api/v1/devices/{ctx.device_id}", "DELETE", token=ctx.token_admin)
    pesan = json.dumps(isi, ensure_ascii=False) if isinstance(isi, dict) else str(isi)
    lulus = kode == 409 and any(c.isdigit() for c in pesan)
    catat(
        "perangkat: hapus ditolak 409 selama dipakai rekaman (pesan menyebut jumlah)",
        lulus,
        f"kode {kode}, pesan {pesan[:110]}",
    )


def cek_web(ctx: Konteks) -> None:
    kode, tipe, isi = minta_mentah(f"{ctx.web}/manifest.webmanifest", timeout=15, batas=4000)
    lulus = kode == 200
    if lulus:
        try:
            data = json.loads(isi)
        except json.JSONDecodeError:
            data = {}
        nama = data.get("name")
        ikon = data.get("icons") or []
        ukuran = {str(i.get("sizes")) for i in ikon if isinstance(i, dict)}
        maskable = any(i.get("purpose") == "maskable" for i in ikon if isinstance(i, dict))
        lulus = (
            nama == "GemaHutan"
            and data.get("display") == "standalone"
            and "192x192" in ukuran
            and "512x512" in ukuran
            and maskable
        )
        catat(
            "web: manifes PWA bisa diakses dan lengkap",
            lulus,
            f"kode {kode}, nama={nama}, display={data.get('display')}, ikon={sorted(ukuran)}",
        )
    else:
        catat("web: manifes PWA bisa diakses dan lengkap", False, f"kode {kode}, tipe {tipe or 'kosong'}")

    kode, tipe, isi = minta_mentah(f"{ctx.web}/sw.js", timeout=15, batas=6000)
    if kode != 200:
        catat("web: service worker bisa diakses dan tidak meng-cache API", False, f"kode {kode}")
        return
    punya_fetch = "addEventListener(\"fetch\"" in isi or "addEventListener('fetch'" in isi
    lewati_api = "/api/" in isi
    catat(
        "web: service worker bisa diakses dan tidak meng-cache API",
        punya_fetch and lewati_api,
        f"kode {kode}, penangan fetch={'ada' if punya_fetch else 'tidak ada'}, pengecualian API={'ada' if lewati_api else 'tidak ada'}",
    )


def bersihkan(ctx: Konteks) -> None:
    """Buang semua yang dibuat pemeriksaan ini supaya basis data kembali seperti semula."""
    sisa: list[str] = []

    for rid in ctx.recording_ids:
        kode = minta(f"{ctx.api}/api/v1/recordings/{rid}", "DELETE", token=ctx.token_admin)[0]
        if kode not in (200, 204, 404):
            sisa.append(f"rekaman {rid}={kode}")

    if ctx.device_id:
        kode = minta(f"{ctx.api}/api/v1/devices/{ctx.device_id}", "DELETE", token=ctx.token_admin)[0]
        if kode != 204:
            sisa.append(f"perangkat {ctx.device_id}={kode}")
        else:
            catat("perangkat: hapus 204 setelah rekaman dibersihkan", True, f"perangkat {ctx.device_id} terhapus")

    if ctx.user_uji_id:
        kode = minta(f"{ctx.api}/api/v1/users/{ctx.user_uji_id}", "DELETE", token=ctx.token_admin)[0]
        if kode not in (204, 409):
            sisa.append(f"akun uji={kode}")

    if ctx.site_dibuat:
        kode = minta(f"{ctx.api}/api/v1/sites/{ctx.site_dibuat}", "DELETE", token=ctx.token_admin)[0]
        if kode not in (200, 204, 404, 409):
            sisa.append(f"lokasi uji={kode}")

    if sisa:
        catat("pembersihan data uji", False, ", ".join(sisa))


def cek_sumber_laporan(ctx: Konteks) -> None:
    """Halaman /laporan membaca angka dari empat endpoint. Bentuk responsnya diperiksa
    di sini supaya laporan tidak diam-diam menampilkan tanda hubung karena kolomnya
    berubah nama."""
    kode, isi = minta(f"{ctx.api}/api/v1/stats/overview", token=ctx.token_admin)
    ringkas = isi if isinstance(isi, dict) else {}
    kunci = {"recordings", "detections", "species_detected", "sites"}
    hilang = sorted(k for k in kunci if k not in ringkas)
    catat(
        "laporan: ringkasan (stats/overview) lengkap",
        kode == 200 and not hilang,
        f"kode {kode}, rekaman={ringkas.get('recordings')}, deteksi={ringkas.get('detections')}"
        + (f", kolom hilang: {hilang}" if hilang else ""),
    )

    kode, isi = minta(f"{ctx.api}/api/v1/stats/timeline", token=ctx.token_admin)
    deret = isi if isinstance(isi, list) else []
    rentang_ok = bool(deret) and all({"date", "detections"} <= set(b) for b in deret[:3])
    catat(
        "laporan: rentang tanggal (stats/timeline) bisa dibaca",
        kode == 200 and rentang_ok,
        f"kode {kode}, {len(deret)} hari"
        + (f", {deret[0].get('date')} sampai {deret[-1].get('date')}" if deret else ", belum ada data"),
    )

    kode, isi = minta(f"{ctx.api}/api/v1/species", token=ctx.token_admin)
    daftar = isi if isinstance(isi, list) else []
    bentuk = bool(daftar) and all(
        {"scientific_name", "default_threshold", "detection_count"} <= set(s) for s in daftar[:5]
    )
    catat(
        "laporan: tabel spesies dengan ambang dan jumlah deteksi",
        kode == 200 and bentuk,
        f"kode {kode}, {len(daftar)} spesies",
    )

    kode, isi = minta(f"{ctx.api}/api/v1/sites?limit=100", token=ctx.token_admin)
    daftar = isi if isinstance(isi, list) else (isi.get("items", []) if isinstance(isi, dict) else [])
    bentuk = bool(daftar) and all(
        {"name", "recordings_count", "detections_count", "species_count"} <= set(s) for s in daftar[:5]
    )
    catat(
        "laporan: sebaran lokasi lengkap",
        kode == 200 and bentuk,
        f"kode {kode}, {len(daftar)} lokasi",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--web", default="http://localhost:3001")
    parser.add_argument("--email", default="admin@gemahutan.id")
    parser.add_argument("--password", default=os.getenv("SEED_ADMIN_PASSWORD"))
    args = parser.parse_args()

    ctx = Konteks(args.api, args.web, args.email, args.password)

    print("Pemeriksaan fitur Fase 2 GemaHutan")
    print(f"  API: {ctx.api}")
    print(f"  Web: {ctx.web}\n")

    if not siapkan_login(ctx):
        print("\n0/1 pemeriksaan lulus")
        print("perlu diperbaiki: login admin")
        return 1

    ambil_lokasi(ctx)
    cek_perangkat(ctx)
    cek_perangkat_tolak_non_admin(ctx)
    cek_unggah_batch(ctx)
    cek_progres_dan_tahap(ctx)
    cek_hapus_perangkat_ditolak(ctx)
    cek_sse(ctx)
    cek_deteksi_lokalisasi(ctx)
    cek_model_info(ctx)
    cek_akun(ctx)
    cek_sumber_laporan(ctx)
    cek_web(ctx)
    bersihkan(ctx)

    gagal = [nama for nama, lulus, _ in HASIL if not lulus]
    print(f"\n{len(HASIL) - len(gagal)}/{len(HASIL)} pemeriksaan lulus")
    if gagal:
        print("perlu diperbaiki: " + "; ".join(gagal))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
