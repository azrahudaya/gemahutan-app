"""Verifikasi alur lupa sandi lewat API sungguhan, bukan lewat test.

Test memanggil layanannya langsung untuk mendapat token. Skrip ini menempuh jalur
yang benar-benar dipakai pengguna: kirim permintaan, ambil tautan dari log
pengembangan (karena SMTP belum dikonfigurasi), lalu pakai tautannya.
"""
import json
import re
import subprocess
import urllib.error
import urllib.request
import uuid

DASAR = "http://localhost:8000"
SANDI_AWAL = "Kicau9Hutan"
SANDI_BARU = "Merpati7Biru"


def panggil(jalur: str, metode: str = "GET", isi: dict | None = None, token: str | None = None):
    data = json.dumps(isi).encode() if isi is not None else None
    req = urllib.request.Request(f"{DASAR}{jalur}", data=data, method=metode)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}


email = f"e2e-{uuid.uuid4().hex[:10]}@gemahutan.id"
print(f"akun uji: {email}")

kode, _ = panggil("/api/v1/auth/register", "POST", {"email": email, "password": SANDI_AWAL, "name": "E2E"})
print(f"1. daftar                          -> {kode}")
assert kode == 201

kode, isi = panggil("/api/v1/auth/login", "POST", {"email": email, "password": SANDI_AWAL})
token_lama = isi.get("access_token")
print(f"2. masuk                           -> {kode}")
assert kode == 200

kode, _ = panggil("/api/v1/me", token=token_lama)
print(f"3. sesi lama sebelum reset         -> {kode}")
assert kode == 200

kode, isi = panggil("/api/v1/auth/forgot-password", "POST", {"email": email})
print(f"4. minta atur ulang                -> {kode}")
print(f"   pesan: {isi.get('message')[:60]}...")
assert kode == 202

kode, isi = panggil("/api/v1/auth/forgot-password", "POST", {"email": f"tidak-ada-{uuid.uuid4().hex[:8]}@gemahutan.id"})
print(f"5. alamat tidak terdaftar          -> {kode}")
assert kode == 202, "jawaban untuk alamat tidak terdaftar harus sama"

# Ambil tautan dari log container, karena SMTP belum dikonfigurasi.
log = subprocess.run(
    ["docker", "compose", "logs", "--since", "2m", "api"],
    capture_output=True, text=True, cwd="/home/fuudaya/Projects/gemahutan",
).stdout
cocok = re.findall(r"token=([A-Za-z0-9_\-]{20,})", log)
if not cocok:
    print("GAGAL: tautan tidak ditemukan di log")
    raise SystemExit(1)
token_reset = cocok[-1]
print(f"6. tautan terbaca dari log         -> token {token_reset[:12]}... (panjang {len(token_reset)})")

kode, _ = panggil("/api/v1/auth/reset-password", "POST", {"token": "token-palsu-yang-panjang", "password": SANDI_BARU})
print(f"7. token palsu                     -> {kode}")
assert kode == 400

kode, isi = panggil("/api/v1/auth/reset-password", "POST", {"token": token_reset, "password": SANDI_BARU})
print(f"8. atur ulang sandi                -> {kode} | sesi dicabut: {isi.get('sessions_revoked')}")
assert kode == 200

kode, isi = panggil("/api/v1/auth/reset-password", "POST", {"token": token_reset, "password": "Kenari8Hijau"})
print(f"9. token dipakai dua kali          -> {kode}")
assert kode == 400

kode, _ = panggil("/api/v1/me", token=token_lama)
print(f"10. sesi lama sesudah reset        -> {kode}")
assert kode == 401

kode, _ = panggil("/api/v1/auth/login", "POST", {"email": email, "password": SANDI_AWAL})
print(f"11. sandi lama                     -> {kode}")
assert kode == 401

kode, isi = panggil("/api/v1/auth/login", "POST", {"email": email, "password": SANDI_BARU})
print(f"12. sandi baru                     -> {kode}")
assert kode == 200
assert isi.get("access_token")

print()
print("SEMUA TAHAP LULUS")