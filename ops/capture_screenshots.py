"""Ambil screenshot asli aplikasi untuk proposal dan slide.

Menjalankan alur nyata di Chromium: login, lalu potret halaman utama pada
viewport desktop dan mobile. Semua gambar berasal dari aplikasi yang benar-benar
jalan, bukan mockup.
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3001"

EMAIL = "admin@gemahutan.id"
PASSWORD = os.getenv("E2E_PASSWORD") or os.getenv("SEED_ADMIN_PASSWORD")
if not PASSWORD:
    raise SystemExit("E2E_PASSWORD atau SEED_ADMIN_PASSWORD wajib diisi")
OUT = Path(__file__).resolve().parent.parent / "docs" / "proposal" / "screenshots"

# (nama berkas, path, mobile, potret seluruh halaman)
SHOTS = [
    ("01_landing.png", "/", False, False),
    ("02_login.png", "/login", False, False),
    ("03_dashboard.png", "/dashboard", False, True),
    ("04_upload.png", "/upload", False, False),
    ("05_daftar_rekaman.png", "/recordings", False, False),
    ("06_detail_rekaman.png", "/recordings/11", False, True),
    ("07_daftar_spesies.png", "/species", False, False),
    ("08_detail_spesies.png", "/species/23", False, False),
    ("09_lokasi.png", "/sites", False, False),
    ("10_detail_lokasi.png", "/sites/1", False, True),
    ("11_dashboard_mobile.png", "/dashboard", True, True),
    ("12_detail_rekaman_mobile.png", "/recordings/11", True, True),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        desktop = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        mobile = browser.new_page(viewport={"width": 414, "height": 896}, device_scale_factor=2)

        # Login dulu supaya halaman terautentikasi bisa dipotret.
        desktop.goto(f"{BASE}/login", wait_until="networkidle")
        desktop.fill('input[type="email"]', EMAIL)
        desktop.fill('input[type="password"]', PASSWORD)
        desktop.click('button[type="submit"]')
        desktop.wait_for_url("**/dashboard", timeout=20000)

        # Sesi mobile memakai token yang sama dari localStorage lewat halaman login.
        mobile.goto(f"{BASE}/login", wait_until="networkidle")
        mobile.fill('input[type="email"]', EMAIL)
        mobile.fill('input[type="password"]', PASSWORD)
        mobile.click('button[type="submit"]')
        mobile.wait_for_url("**/dashboard", timeout=20000)

        for name, path, is_mobile, full in SHOTS:
            page = mobile if is_mobile else desktop
            page.goto(f"{BASE}{path}", wait_until="networkidle")
            # Beri waktu chart, peta, dan spektrogram selesai render.
            page.wait_for_timeout(3500)
            page.screenshot(path=str(OUT / name), full_page=full)
            print(f"{name} <- {path} {'(mobile)' if is_mobile else ''}")

        browser.close()
    print(f"tersimpan di {OUT}")


if __name__ == "__main__":
    sys.exit(main())
