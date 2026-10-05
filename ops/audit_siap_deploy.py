#!/usr/bin/env python3
"""Audit kesiapan deploy GemaHutan ke VPS CPU (juri bisa membuka kapan saja).

Ditulis peninjau. Agen boleh menjalankan, tidak boleh mengubah. sha256 berkas ini
dicatat di prompt. Status: LULUS, GAGAL, BELUM (butuh jaringan/layanan yang tidak
tersedia saat ini; tidak dihitung gagal, tetapi harus LULUS sebelum deploy).
Kode keluar 1 kalau ada GAGAL.

Pakai (dari akar repo, stack lokal hidup dengan image terbaru):
    .venv/bin/python ops/audit_siap_deploy.py
"""
import json
import os
import random
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("GEMAHUTAN_ROOT") or Path(__file__).resolve().parent.parent)
API = os.environ.get("GEMAHUTAN_API", "http://localhost:8000")
hasil = []


def catat(kode, nama, status, detail=""):
    hasil.append({"kode": kode, "nama": nama, "status": status, "detail": str(detail)[:400]})


def baca(rel):
    p = ROOT / rel
    return p.read_text(errors="ignore") if p.exists() else ""


def jalankan(cmd, timeout=300):
    p = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()


def cek_url_api():
    api_ts = baca("apps/web/src/lib/api.ts")
    df = baca("apps/web/Dockerfile")
    prod = baca("deploy/docker-compose.prod.yml")
    masalah = []
    if re.search(r'API_BASE\s*=.*"http://localhost:8000"', api_ts) and "ARG NEXT_PUBLIC_API_URL" not in df:
        masalah.append("bundle memakai default localhost:8000 dan Dockerfile tanpa ARG NEXT_PUBLIC_API_URL")
    if "ARG NEXT_PUBLIC_API_URL" in df and not re.search(r"args:[\s\S]{0,200}NEXT_PUBLIC_API_URL", prod):
        masalah.append("compose produksi tidak mengirim NEXT_PUBLIC_API_URL sebagai build arg")
    if re.search(r"NEXT_PUBLIC_API_URL:\s*\$\{NEXT_PUBLIC_API_URL:-[^}]*/api/v1\}", prod) and "/api/v1/" in api_ts:
        masalah.append("nilai bawaan diakhiri /api/v1 padahal kode menambah /api/v1 lagi")
    catat("D01", "URL API benar di build web produksi", "GAGAL" if masalah else "LULUS", "; ".join(masalah))


def cek_caddy():
    c = baca("deploy/Caddyfile")
    peta = baca("apps/web/src/components/sites-map.tsx")
    host = set(re.findall(r"https://([a-z0-9.\-{}]+)/\{z\}", peta)) or {"tile.openstreetmap.org"}
    masalah = []
    if "microphone=()" in c or "microphone=(self)" not in c:
        masalah.append("Permissions-Policy tidak mengizinkan microphone=(self)")
    if "geolocation=()" in c:
        masalah.append("geolocation diblokir")
    csp = re.search(r'Content-Security-Policy "([^"]+)"', c)
    csp = csp.group(1) if csp else ""
    for h in host:
        for arah in ("img-src", "connect-src"):
            bag = re.search(arah + r"([^;]*)", csp)
            if not bag or (h not in bag.group(1) and "*.openstreetmap.org" not in bag.group(1)):
                masalah.append(f"{arah} tidak mengizinkan {h}")
    if "?token=" in baca("apps/web/src/lib/api.ts") and not re.search(r"log\s*\{[\s\S]*?(format|filter)", c):
        masalah.append("token di query string masuk access log Caddy tanpa redaksi")
    catat("D02", "header Caddy tidak mematikan mic, peta, atau membocorkan token", "GAGAL" if masalah else "LULUS",
          "; ".join(masalah))


def cek_register():
    auth_py = baca("apps/api/app/routers/auth.py")
    auth_tsx = baca("apps/web/src/lib/auth.tsx")
    m = re.search(r"const register = async[\s\S]*?\n  };", auth_tsx)
    blok = m.group(0) if m else ""
    api_token = re.search(r'"/register",\s*response_model=TokenResponse', auth_py)
    ok = bool(api_token) or ("login(" in blok and "res.access_token" not in blok)
    catat("D03", "alur daftar tidak melempar pengguna ke login", "LULUS" if ok else "GAGAL",
          "" if ok else "API mengembalikan UserResponse tetapi klien membaca res.access_token")


def cek_refresh():
    ok = "/auth/refresh" in baca("apps/web/src/lib/api.ts")
    catat("D04", "klien memakai refresh token sebelum logout paksa", "LULUS" if ok else "GAGAL")


def cek_xff():
    def post(xff):
        req = urllib.request.Request(f"{API}/api/v1/sites", data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json", "X-Forwarded-For": xff})
        try:
            return urllib.request.urlopen(req, timeout=10).status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception:  # noqa: BLE001
            return None
    kode = [post(f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}") for _ in range(75)]
    if None in kode:
        catat("D05", "pembatas laju tidak bisa dilewati dengan X-Forwarded-For palsu", "BELUM", "API tidak hidup")
        return
    catat("D05", "pembatas laju tidak bisa dilewati dengan X-Forwarded-For palsu",
          "LULUS" if 429 in kode else "GAGAL", f"429 muncul {kode.count(429)} kali dari 75")


def cek_lockout():
    t = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "apps/api/tests").glob("test_*.py"))
    ok = re.search(r"def test_\w*(kunci|lockout)\w*(ip|proxy|forwarded|lain)\w*", t, re.I)
    catat("D06", "penguncian login tidak bisa dipakai mengunci akun orang lain (ada test)",
          "LULUS" if ok else "GAGAL", "" if ok else "tidak ada test penguncian lintas IP/proxy")


def cek_blocking():
    rec = baca("apps/api/app/routers/recordings.py")
    wk = baca("apps/worker/worker.py")
    masalah = []
    if re.search(r"^\s*hasil = subprocess\.run\(", rec, re.M) and not re.search(r"run_in_threadpool|to_thread", rec):
        masalah.append("ffprobe/upload sinkron di handler async")
    if re.search(r"^async def process_recording", wk, re.M) and not re.search(r"to_thread|run_in_executor", wk):
        masalah.append("process_recording async tanpa to_thread/run_in_executor")
    catat("D07", "I/O dan inferensi berat tidak memblokir event loop", "GAGAL" if masalah else "LULUS",
          "; ".join(masalah))


def cek_healthcheck():
    df = baca("apps/worker/Dockerfile")
    prod = baca("deploy/docker-compose.prod.yml")
    buruk = "worker alive" in df or re.search(r"worker:[\s\S]{0,600}print\('worker alive'\)", prod)
    catat("D08", "healthcheck worker memeriksa heartbeat sungguhan", "GAGAL" if buruk else "LULUS")


def cek_rahasia():
    temuan = []
    pakai = re.compile(r"(?i)(password|sandi|pw)[^\n]{0,30}[\"']admin123[\"']"
                       r"|\([\"'][^\"']+@[^\"']+[\"'],\s*[\"']admin123[\"']")
    for pola in ("ops/*.py", "apps/api/app/*.py", "apps/api/app/**/*.py"):
        for f in ROOT.glob(pola):
            if pakai.search(f.read_text(errors="ignore")):
                temuan.append(str(f.relative_to(ROOT)))
    env = baca(".env.prod.example")
    if "ENVIRONMENT=production" not in env:
        temuan.append(".env.prod.example tanpa ENVIRONMENT=production")
    catat("D09", "tidak ada sandi demo di kode non-test, contoh env produksi benar",
          "GAGAL" if temuan else "LULUS", ", ".join(sorted(set(temuan))[:8]))


def cek_npm():
    rc, out = jalankan("cd apps/web && npm audit --omit=dev --json", timeout=180)
    try:
        v = json.loads(out).get("metadata", {}).get("vulnerabilities", {})
    except Exception:  # noqa: BLE001
        catat("D10", "npm audit produksi: 0 critical, 0 high", "BELUM", "npm audit tidak bisa dijalankan")
        return
    n = v.get("critical", 0) + v.get("high", 0)
    catat("D10", "npm audit produksi: 0 critical, 0 high", "LULUS" if n == 0 else "GAGAL",
          f"critical {v.get('critical', 0)}, high {v.get('high', 0)}")


def cek_vps():
    j = json.loads(baca("ml/reports/latensi_vps.json") or "{}")
    masalah = []
    if not j:
        masalah.append("latensi_vps.json tidak ada")
    else:
        if j.get("cpus") != 4 or j.get("memori_mb", 99999) > 8192:
            masalah.append("bukan simulasi 4 vCPU / <= 8 GB")
        if j.get("durasi_audio_s", 0) < 3600:
            masalah.append("audio < 60 menit")
        if j.get("rss_maks_mb", 1e9) >= 3500:
            masalah.append(f"RSS {j.get('rss_maks_mb')} MB >= 3500 (tidak muat server 4 GB)")
        if j.get("waktu_s", 1e9) > 900:
            masalah.append(f"waktu {j.get('waktu_s')} dtk > 900")
    prod = baca("deploy/docker-compose.prod.yml")
    mem = re.search(r"worker:[\s\S]*?memory:\s*(\d+)([mg])", prod)
    if j and mem:
        batas = int(mem.group(1)) * (1024 if mem.group(2) == "g" else 1)
        if batas < j.get("rss_maks_mb", 0) * 1.2:
            masalah.append(f"batas memori worker {batas} MB < 1,2 x RSS terukur")
    catat("D11", "benchmark 60 menit di 4 vCPU: < 900 dtk, RSS muat server", "GAGAL" if masalah else "LULUS",
          "; ".join(masalah))


def cek_cascade_gerbang():
    m = json.loads(baca("ml/checkpoints/MANIFEST.json") or "{}")
    cfg = ROOT / "ml/configs/cascade.yaml"
    if not cfg.exists():
        catat("D12", "konfigurasi cascade produksi sudah lewat gerbang", "LULUS", "tidak ada cascade.yaml")
        return
    import hashlib
    s = hashlib.sha256(cfg.read_bytes()).hexdigest()
    ok = m.get("cascade_config_sha256") == s
    catat("D12", "konfigurasi cascade produksi sudah lewat gerbang", "LULUS" if ok else "GAGAL",
          "" if ok else "MANIFEST.cascade_config_sha256 tidak cocok dengan ml/configs/cascade.yaml")


def cek_smoke():
    j = json.loads(baca("ops/reports/smoke_prod.json") or "{}")
    rc, out = jalankan("git log -1 --format=%ct -- apps deploy docker-compose.yml ml/checkpoints ml/configs")
    terakhir = int(out or 0)
    masalah = []
    if not j:
        masalah.append("ops/reports/smoke_prod.json tidak ada")
    else:
        if not j.get("lulus"):
            masalah.append("smoke tidak lulus")
        if int(j.get("waktu_unix", 0)) < terakhir:
            masalah.append("smoke lebih tua dari perubahan terakhir di apps/deploy/model")
        for k in ("daftar_masuk", "unggah_proses_hasil", "rekam_halaman", "peta_ubin", "verifikasi", "ekspor"):
            if j.get("langkah", {}).get(k) is not True:
                masalah.append(f"langkah {k} tidak lulus")
    catat("D13", "smoke test stack produksi dari build bersih", "GAGAL" if masalah else "LULUS", "; ".join(masalah))


def cek_juri():
    d = baca("docs/AKSES_JURI.md")
    ok = bool(d) and "admin123" not in d and re.search(r"(?i)akun", d) and re.search(r"(?i)contoh (audio|rekaman)", d)
    catat("D14", "panduan akses juri (tanpa sandi di repo) dan contoh audio", "LULUS" if ok else "GAGAL")


def main():
    print(f"audit_siap_deploy.py sha256 "
          f"{__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest()[:16]}")
    for f in (cek_url_api, cek_caddy, cek_register, cek_refresh, cek_xff, cek_lockout, cek_blocking,
              cek_healthcheck, cek_rahasia, cek_npm, cek_vps, cek_cascade_gerbang, cek_smoke, cek_juri):
        f()
    lebar = max(len(h["nama"]) for h in hasil)
    for h in hasil:
        print(f"[{h['status']:5}] {h['kode']} {h['nama']:<{lebar}}  {h['detail']}")
    g = sum(h["status"] == "GAGAL" for h in hasil)
    print(f"\n{sum(h['status'] == 'LULUS' for h in hasil)} LULUS, {g} GAGAL, "
          f"{sum(h['status'] == 'BELUM' for h in hasil)} BELUM")
    return 1 if g else 0


if __name__ == "__main__":
    sys.exit(main())
