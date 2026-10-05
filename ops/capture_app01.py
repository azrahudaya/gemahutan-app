"""Screenshot halaman aplikasi untuk APP_01 blok E.

Ambil tiap halaman (app) pada lebar 1280px dan 390px, simpan di
ops/reports/tangkapan_app01/. Login sebagai admin dulu supaya halaman
terautentikasi bisa dipotret.
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3001"
EMAIL = "admin@gemahutan.id"
PASSWORD = os.getenv("E2E_PASSWORD") or os.getenv("SEED_ADMIN_PASSWORD") or "admin123"
OUT = Path(__file__).resolve().parent.parent / "ops" / "reports" / "tangkapan_app01"

PAGES = [
    "/dashboard",
    "/recordings",
    "/upload",
    "/rekam",
    "/species",
    "/sites",
    "/devices",
    "/model",
    "/laporan",
    "/admin/users",
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        desktop = browser.new_page(viewport={"width": 1280, "height": 900})
        mobile = browser.new_page(viewport={"width": 390, "height": 844})

        # Login di kedua viewport.
        for page in (desktop, mobile):
            page.goto(f"{BASE}/login", wait_until="networkidle")
            page.fill('input[type="email"]', EMAIL)
            page.fill('input[type="password"]', PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_url("**/dashboard", timeout=20000)

        # Ambil id rekaman dan lokasi pertama supaya halaman detail bisa dipotret.
        first_recording = None
        first_site = None
        try:
            first_recording = desktop.evaluate(
                "async () => { const r = await fetch('/api/v1/recordings?page_size=1', {headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}}); if(!r.ok) return null; const d = await r.json(); return d.items && d.items[0] ? d.items[0].id : null; }"
            )
        except Exception:
            pass
        try:
            first_site = desktop.evaluate(
                "async () => { const r = await fetch('/api/v1/sites', {headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}}); if(!r.ok) return null; const d = await r.json(); return d && d[0] ? d[0].id : null; }"
            )
        except Exception:
            pass

        if first_recording is not None:
            PAGES.append(f"/recordings/{first_recording}")
        if first_site is not None:
            PAGES.append(f"/sites/{first_site}")

        for path in PAGES:
            slug = path.strip("/").replace("/", "_") or "index"
            for page, width in ((desktop, "1280"), (mobile, "390")):
                page.goto(f"{BASE}{path}", wait_until="load")
                page.wait_for_timeout(3500)
                page.screenshot(path=str(OUT / f"{slug}__{width}.png"), full_page=False)
                print(f"{slug}__{width}.png <- {path}")

        browser.close()
    print(f"tersimpan di {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
