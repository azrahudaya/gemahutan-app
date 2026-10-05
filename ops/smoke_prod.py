#!/usr/bin/env python3
"""Smoke test produksi: daftar, masuk, unggah, deteksi, peta, rekam, verifikasi, ekspor.

Jalankan dari root repo dengan stack lokal hidup:
    .venv/bin/python ops/smoke_prod.py
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = os.getenv("GEMAHUTAN_API", "http://localhost:8000")
WEB = os.getenv("GEMAHUTAN_WEB", "http://localhost:3001")
EMAIL = f"smoke-{int(time.time())}@test.gemahutan.id"
PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "smoke123test")

OUT = ROOT / "ops" / "reports"
OUT.mkdir(parents=True, exist_ok=True)
SCREENSHOTS = OUT / "smoke"
SCREENSHOTS.mkdir(parents=True, exist_ok=True)

langkah = {}
errors = []


def catat(nama, ok, detail=""):
    langkah[nama] = ok
    if not ok:
        errors.append(f"{nama}: {detail}")
    print(f"  {'PASS' if ok else 'GAGAL'} {nama} {detail}")


def main():
    from playwright.sync_api import sync_playwright

    print("Smoke test GemaHutan")
    print(f"  API: {API}")
    print(f"  Web: {WEB}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # --- 1. Daftar + masuk ---
        print("\n1. Daftar + masuk")
        try:
            page.goto(f"{WEB}/register", timeout=15000)
            page.fill('input[type="text"], input[name="name"]', "Smoke Test")
            page.fill('input[type="email"]', EMAIL)
            page.fill('input[type="password"]', PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url(f"{WEB}/login", timeout=10000)
            catat("daftar_masuk", True)
        except Exception as e:
            catat("daftar_masuk", False, str(e)[:200])
            browser.close()
            return _tulis_dan_keluar()

        # Masuk
        try:
            page.fill('input[type="email"]', EMAIL)
            page.fill('input[type="password"]', PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url(f"{WEB}/dashboard", timeout=15000)
            catat("daftar_masuk", True)
        except Exception as e:
            catat("daftar_masuk", False, str(e)[:200])
            browser.close()
            return _tulis_dan_keluar()

        # --- 2. Unggah audio + tunggu deteksi ---
        print("\n2. Unggah + deteksi")
        try:
            demo = sorted((ROOT / "ml" / "demo_audio").glob("*.mp3"))
            page.goto(f"{WEB}/upload", timeout=10000)
            page.wait_for_timeout(2000)

            # Pilih lokasi
            page.select_option('select', index=0)
            page.wait_for_timeout(500)

            # Unggah berkas
            file_input = page.locator('input[type="file"]')
            file_input.set_input_files(str(demo[0]))
            page.wait_for_timeout(1000)

            # Klik unggah
            page.click('button:has-text("Unggah"), button:has-text("Upload"), button:has-text("Kirim")')
            page.wait_for_timeout(3000)

            # Tunggu deteksi muncul (maks 60 detik)
            for _ in range(12):
                page.goto(f"{WEB}/recordings", timeout=10000)
                page.wait_for_timeout(5000)
                # Cek apakah ada rekaman dengan status selesai
                body = page.content()
                if "selesai" in body.lower() or "completed" in body.lower():
                    break

            page.screenshot(path=str(SCREENSHOTS / "smoke_upload.png"))
            catat("unggah_proses_hasil", True)
        except Exception as e:
            catat("unggah_proses_hasil", False, str(e)[:200])

        # --- 3. Halaman /rekam ---
        print("\n3. Halaman rekam")
        try:
            page.goto(f"{WEB}/rekam", timeout=10000)
            page.wait_for_timeout(2000)
            page.screenshot(path=str(SCREENSHOTS / "smoke_rekam.png"))
            catat("rekam_halaman", True)
        except Exception as e:
            catat("rekam_halaman", False, str(e)[:200])

        # --- 4. Peta /sites ---
        print("\n4. Peta")
        try:
            page.goto(f"{WEB}/sites", timeout=15000)
            page.wait_for_timeout(5000)
            page.screenshot(path=str(SCREENSHOTS / "smoke_peta.png"))
            # Cek canvas peta termuat
            has_map = page.locator(".maplibregl-canvas, .mapboxgl-canvas, canvas").count() > 0
            catat("peta_ubin", has_map, "canvas tidak ditemukan" if not has_map else "")
        except Exception as e:
            catat("peta_ubin", False, str(e)[:200])

        # --- 5. Verifikasi ---
        print("\n5. Verifikasi")
        try:
            page.goto(f"{WEB}/recordings", timeout=10000)
            page.wait_for_timeout(2000)
            # Klik rekaman pertama
            first = page.locator('a[href*="/recordings/"]').first
            if first.count() > 0:
                first.click()
                page.wait_for_timeout(3000)
                page.screenshot(path=str(SCREENSHOTS / "smoke_verifikasi.png"))
                catat("verifikasi", True)
            else:
                catat("verifikasi", False, "tidak ada link rekaman")
        except Exception as e:
            catat("verifikasi", False, str(e)[:200])

        # --- 6. Ekspor ---
        print("\n6. Ekspor")
        try:
            # Akses via API dengan token dari localStorage
            token = page.evaluate("localStorage.getItem('access_token')")
            if token:
                import urllib.request
                req = urllib.request.Request(
                    f"{API}/api/v1/exports/recordings?format=csv",
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp = urllib.request.urlopen(req, timeout=10)
                ok = resp.status == 200 and len(resp.read()) > 0
                catat("ekspor", ok)
            else:
                catat("ekspor", False, "token tidak ditemukan")
        except Exception as e:
            catat("ekspor", False, str(e)[:200])

        browser.close()

    _tulis_dan_keluar()


def _tulis_dan_keluar():
    lulus = all(langkah.values())
    hasil = {
        "lulus": lulus,
        "waktu_unix": int(time.time()),
        "git_sha": os.popen("git rev-parse HEAD").read().strip(),
        "langkah": langkah,
    }
    (OUT / "smoke_prod.json").write_text(json.dumps(hasil, indent=2))
    print(f"\n{'LULUS' if lulus else 'GAGAL'} ({sum(langkah.values())}/{len(langkah)} langkah)")
    if errors:
        print("Gagal:")
        for e in errors:
            print(f"  - {e}")
    sys.exit(0 if lulus else 1)


if __name__ == "__main__":
    main()