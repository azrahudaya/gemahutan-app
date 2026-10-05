"""Pemeriksa keamanan GemaHutan. Dijalankan dari host, bukan di dalam container.

Menjalankan enam pemeriksaan terhadap stack yang sedang hidup dan mencetak
LULUS atau GAGAL untuk masing-masing. Kode keluar 1 kalau ada yang gagal,
supaya bisa dipakai sebagai gerbang sebelum demo atau sebelum deploy.

Pakai:
    python3 ops/security_check.py
    python3 ops/security_check.py --api http://localhost:8000
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HASIL: list[tuple[str, bool, str]] = []


def catat(nama: str, lulus: bool, keterangan: str) -> None:
    HASIL.append((nama, lulus, keterangan))
    print(f"  [{'LULUS' if lulus else 'GAGAL'}] {nama}: {keterangan}")


def minta(url: str, method: str = "GET", body: dict | None = None, token: str | None = None,
          timeout: int = 15) -> tuple[int, dict | str]:
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


def cek_endpoint_terlindungi(api: str) -> None:
    """Data lapangan tidak boleh bisa dibaca tanpa login."""
    terlindungi = [
        "/api/v1/recordings",
        "/api/v1/species",
        "/api/v1/sites",
        "/api/v1/stats/overview",
        "/api/v1/jobs",
        "/api/v1/exports/verified",
        "/api/v1/exports/recordings",
        "/api/v1/me",
    ]
    bocor = []
    for path in terlindungi:
        kode, _ = minta(f"{api}{path}")
        if kode != 401:
            bocor.append(f"{path}={kode}")
    catat(
        "endpoint data menolak akses tanpa token",
        not bocor,
        "semua 401" if not bocor else "bocor: " + ", ".join(bocor),
    )


def cek_rate_limit(api: str, email: str) -> None:
    """Percobaan login gagal berulang harus dikunci sementara."""
    kode = [
        minta(f"{api}/api/v1/auth/login", "POST", {"email": email, "password": "salah-terus"})[0]
        for _ in range(7)
    ]
    lulus = 429 in kode
    catat(
        "login dikunci setelah percobaan gagal berulang",
        lulus,
        f"kode: {kode}" + ("" if lulus else " (tidak pernah 429)"),
    )


def cek_pencabutan_token(api: str, email: str, password: str) -> None:
    """Logout harus mematikan access dan refresh token."""
    kode, isi = minta(f"{api}/api/v1/auth/login", "POST", {"email": email, "password": password})
    if kode != 200 or not isinstance(isi, dict):
        catat("logout mencabut token", False, f"login gagal ({kode})")
        return

    access, refresh = isi["access_token"], isi["refresh_token"]
    sebelum = minta(f"{api}/api/v1/me", token=access)[0]
    minta(f"{api}/api/v1/auth/logout", "POST", {"refresh_token": refresh}, token=access)
    sesudah = minta(f"{api}/api/v1/me", token=access)[0]
    refresh_baru = minta(
        f"{api}/api/v1/auth/refresh", "POST", {"refresh_token": refresh}
    )[0]
    lulus = sebelum == 200 and sesudah == 401 and refresh_baru == 401
    catat(
        "logout mencabut access dan refresh token",
        lulus,
        f"sebelum={sebelum}, sesudah={sesudah}, refresh={refresh_baru}",
    )


def cek_port_tidak_terbuka(port: int = 3001) -> None:
    """Port dev harus terikat ke localhost saja, bukan ke seluruh jaringan."""
    try:
        out = subprocess.run(
            ["ss", "-ltn"], capture_output=True, text=True, timeout=10
        ).stdout
    except Exception as exc:
        catat("port terikat ke localhost", False, f"ss tidak bisa dijalankan: {exc}")
        return

    terbuka = [baris.split()[3] for baris in out.splitlines() if f":{port}" in baris]
    bahaya = [alamat for alamat in terbuka if not alamat.startswith("127.0.0.1") and "::1" not in alamat]
    catat(
        "port terikat ke localhost",
        not bahaya,
        f"port {port}: {terbuka or 'tidak mendengarkan'}",
    )


def cek_rahasia_lokal(env_path: str = ".env") -> None:
    """Nilai contoh tidak boleh tertinggal di berkas env."""
    try:
        with open(env_path, encoding="utf-8") as berkas:
            isi = berkas.read()
    except OSError:
        catat("rahasia lokal bukan nilai contoh", False, f"{env_path} tidak ditemukan")
        return

    sisa = re.findall(r"^(JWT_SECRET|SECRET_KEY)=(change-me-in-production|secret|)$", isi, re.M)
    pendek = [
        nama
        for nama, nilai in re.findall(r"^(JWT_SECRET|SECRET_KEY)=(.+)$", isi, re.M)
        if len(nilai) < 32
    ]
    masalah = [f"{n} nilai contoh" for n, _ in sisa] + [f"{n} terlalu pendek" for n in pendek]
    catat(
        "rahasia lokal bukan nilai contoh",
        not masalah,
        "kuat" if not masalah else "; ".join(masalah),
    )


def cek_rahasia_tidak_masuk_git() -> None:
    """Tidak ada kredensial sungguhan yang ikut dilacak git.

    Nilai contoh di berkas .example sengaja diabaikan: yang dicari adalah
    kredensial asli yang tidak sengaja ter-commit.
    """
    try:
        out = subprocess.run(
            # Hanya nilai yang benar-benar terisi yang dianggap temuan, bukan
            # nama variabel yang disebut di dokumentasi.
            ["git", "grep", "-InE",
             r"((KAGGLE_KEY|XC_API_KEY|AWS_SECRET|JWT_SECRET)=[A-Za-z0-9_\-]{12,}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,})",
             "--", "."],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout.strip()
    except Exception as exc:
        catat("tidak ada kredensial di repo", False, f"git grep gagal: {exc}")
        return

    penanda_contoh = (
        "your-", "your_", "contoh", "example", "xxx", "placeholder",
        "change-me", "isi-", "ganti", "<", "{{",
    )
    temuan = []
    for baris in out.splitlines():
        if any(penanda in baris.lower() for penanda in penanda_contoh):
            continue
        temuan.append(baris)

    catat(
        "tidak ada kredensial di repo",
        not temuan,
        "bersih" if not temuan else temuan[0][:120],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--email", default="admin@gemahutan.id")
    parser.add_argument("--password", default=os.getenv("SEED_ADMIN_PASSWORD"))
    parser.add_argument("--web-port", type=int, default=3001)
    args = parser.parse_args()

    print(f"Pemeriksaan keamanan GemaHutan pada {args.api}")
    # Beri jeda supaya penguncian login dari percobaan sebelumnya kedaluwarsa.
    time.sleep(1)
    cek_endpoint_terlindungi(args.api)
    cek_pencabutan_token(args.api, args.email, args.password)
    cek_rate_limit(args.api, f"uji-keamanan-{int(time.time())}@gemahutan.id")
    cek_port_tidak_terbuka(args.web_port)
    cek_rahasia_lokal()
    cek_rahasia_tidak_masuk_git()

    gagal = [nama for nama, lulus, _ in HASIL if not lulus]
    print(f"\n{len(HASIL) - len(gagal)}/{len(HASIL)} pemeriksaan lulus")
    if gagal:
        print("perlu diperbaiki: " + "; ".join(gagal))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
