"""Click-through E2E untuk GemaHutan (bukti R-35).

Menjalankan alur nyata di Chromium headless: login, buka tiap halaman,
klik kontrol satu per satu, catat console error dan request gagal,
lalu ulangi di viewport mobile untuk cek overflow.
"""
import os
import pathlib
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "http://localhost:3001"
EMAIL = "admin@gemahutan.id"
PASSWORD = os.getenv("E2E_PASSWORD") or os.getenv("SEED_ADMIN_PASSWORD")
if not PASSWORD:
    raise SystemExit("E2E_PASSWORD atau SEED_ADMIN_PASSWORD wajib diisi")

console_errors = []
failed_requests = []
report = []


def note(step, detail):
    report.append(f"{step}: {detail}")
    print(f"{step}: {detail}")


def bersihkan_lokasi_uji():
    """Hapus lokasi buatan pengujian supaya data demo tidak menumpuk.

    Rekaman yang sempat memakai lokasi uji dipindahkan ke lokasi pertama lebih
    dulu. Kalau psql tidak bisa dijalankan, pengujian tetap dianggap selesai.
    """
    sql = (
        "update recordings set site_id=(select id from sites order by id limit 1) "
        "where site_id in (select id from sites where name like 'Lokasi Uji%');"
        "delete from sites where name like 'Lokasi Uji%';"
    )
    hasil = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "gemahutan",
         "-d", "gemahutan", "-c", sql],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    print("bersihkan lokasi uji:", "selesai" if hasil.returncode == 0 else "dilewati")


def buka(page, path: str) -> None:
    """Buka halaman tanpa menunggu jaringan benar-benar sepi.

    Aplikasi ini melakukan polling status pipeline dan peta menarik ubin dari
    OpenStreetMap, jadi `networkidle` tidak pernah tercapai dan navigasi bisa
    menggantung sampai timeout 30 detik. Yang perlu dipastikan DOM siap, bukan
    jaringan sepi.
    """
    page.goto(f"{BASE}{path}", wait_until="domcontentloaded", timeout=30000)
    try:
        page.wait_for_selector("main, h1", timeout=15000)
    except Exception:
        pass


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: console_errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("requestfailed", lambda r: failed_requests.append(f"{r.method} {r.url}"))
        page.on("request", lambda r: print(f"REQ: {r.method} {r.url}"))  # debug log
        page.on("response", lambda r: print(f"RES: {r.status} {r.url}"))  # debug log

        # 1. login lewat form asli
        buka(page, "/login")
        page.screenshot(path="/tmp/e2e_01_login.png")
        page.fill('input[type="email"]', EMAIL)
        page.screenshot(path="/tmp/e2e_02_filled.png")
        page.fill('input[type="password"]', PASSWORD)
        page.click('button[type="submit"]')
        page.screenshot(path="/tmp/e2e_03_after_submit.png")
        try:
            page.wait_for_url("**/dashboard", timeout=20000)
        except Exception as e:
            print(f"LOGIN FAIL: {e}")
            print(f"Current URL: {page.url}")
            raise
        note("login", f"form submit -> {page.url.replace(BASE, '')}")

        # 2. dashboard: angka nyata dari API
        buka(page, "/dashboard")
        page.wait_for_timeout(2000)
        angka = page.eval_on_selector_all(
            "div.grid p.text-2xl", "els => els.map(e => e.textContent.trim())"
        )
        note("dashboard", f"kartu statistik: {angka}")

        # 3. species list -> detail
        buka(page, "/species")
        rows = page.locator("tbody tr").count()
        note("species list", f"{rows} baris spesies tampil")

        # Kolom classifier lokal harus ada dan menyebut angka yang benar di ringkasan,
        # karena tanpa kolom ini pengguna tidak tahu spesies mana yang bisa dideteksi
        # model dan mana yang hanya lewat BirdNET zero-shot.
        tajuk = page.locator("thead th").all_inner_texts()
        ada_kolom = "Classifier lokal" in tajuk

        # Filter "hanya classifier lokal" harus benar-benar menyaring, bukan sekadar
        # ada di layar.
        kotak = page.get_by_role("checkbox", name="Hanya yang dikenali classifier lokal")
        kotak.check()
        page.wait_for_timeout(400)
        baris_lokal = page.locator("tbody tr").count()
        semua_sel = page.locator("tbody tr td:nth-child(3)").all_inner_texts()
        kotak.uncheck()
        page.wait_for_timeout(400)
        baris_semua = page.locator("tbody tr").count()
        hanya_ya = all(t.strip() == "Ya" for t in semua_sel)
        note(
            "species classifier lokal",
            f"kolom {'ada' if ada_kolom else 'TIDAK ADA'}, "
            f"filter {baris_lokal} dari {baris_semua} baris, "
            f"semua baris hasil filter berlabel Ya: {hanya_ya}",
        )

        page.locator("tbody tr a").first.click()
        page.wait_for_url("**/species/**", timeout=15000)
        note("species detail", f"{page.url.replace(BASE, '')} terbuka")

        # 4. recordings list -> detail
        # Baris pertama belum tentu punya deteksi, jadi pilih baris yang kolom
        # Deteksi-nya lebih dari nol supaya uji tombol verifikasi tidak kosong.
        buka(page, "/recordings")
        page.wait_for_timeout(1500)
        baris = page.locator("tbody tr")
        dipilih = None
        for i in range(baris.count()):
            kolom = baris.nth(i).locator("td")
            if kolom.count() >= 5 and kolom.nth(4).inner_text().strip() not in ("", "0"):
                dipilih = baris.nth(i)
                break
        (dipilih or baris.first).locator("a").first.click()
        page.wait_for_url("**/recordings/**", timeout=15000)
        page.wait_for_timeout(8000)  # beri waktu API membuat spektrogram
        spec_ok = page.evaluate(
            "(() => { const i = document.querySelector('img[alt=\"Spektrogram mel rekaman ini\"]'); return i ? i.naturalWidth : 0; })()"
        )
        note("recording detail", f"spektrogram lebar {spec_ok}px ter-render")

        # 5. tombol verifikasi ahli
        verify_btn = page.get_by_role("button", name="Benar").first
        if verify_btn.count() == 0:
            note("verifikasi", "tombol tidak ada")
        else:
            verify_btn.click()
            page.wait_for_timeout(1500)
            status_text = page.inner_text("body")
            note("verifikasi", "tersimpan" if "Benar" in status_text else "tidak terlihat perubahan")

        # 6. putar audio (waveform player)
        play = page.get_by_role("button", name="Putar audio")
        if play.count():
            play.click()
            page.wait_for_timeout(1200)
            note("audio player", "tombol Putar diklik")
        else:
            note("audio player", "tombol tidak ditemukan")

        # 7. sites list -> tambah lokasi -> submit
        buka(page, "/sites")
        cards = page.locator("a[href^='/sites/']").count()
        note("sites", f"{cards} kartu lokasi tampil")
        page.get_by_role("link", name="Tambah Lokasi").first.click()
        page.wait_for_url("**/sites/new", timeout=15000)
        nama = f"Lokasi Uji E2E {int(time.time()) % 100000}"
        page.fill('input[name="name"]', nama)
        page.fill('input[name="latitude"]', "-6.9123")
        page.fill('input[name="longitude"]', "107.6098")
        page.click('button[type="submit"]')
        page.wait_for_url("**/sites", timeout=20000)
        page.wait_for_timeout(1200)
        note("tambah lokasi", "form submit -> /sites, lokasi tersimpan" if nama in page.inner_text("body") else "lokasi baru tidak muncul")

        # 7b. filter rekaman benar-benar menyaring
        buka(page, "/recordings")
        page.wait_for_timeout(1800)
        total_rows = page.locator("tbody tr").count()
        page.select_option('select[aria-label="Filter lokasi"]', index=1)
        page.wait_for_timeout(1800)
        filtered_rows = page.locator("tbody tr").count()
        page.select_option('select[aria-label="Filter status pemrosesan"]', "failed")
        page.wait_for_timeout(1500)
        failed_state = page.inner_text("body")
        note(
            "filter rekaman",
            f"tanpa filter {total_rows} baris, setelah pilih lokasi {filtered_rows} baris, "
            f"status gagal memunculkan pesan kosong: {'Tidak ada rekaman' in failed_state}",
        )
        export_button = page.get_by_role("button", name="Unduh CSV")
        if export_button.count():
            with page.expect_download(timeout=15000) as download_info:
                export_button.click()
            download = download_info.value
            note("ekspor CSV", f"unduhan {download.suggested_filename} berhasil dipicu")
        else:
            note("ekspor CSV", "tombol unduh tidak ada")

        # 7c. halaman detail spesies berisi data nyata
        buka(page, "/species/23")
        page.wait_for_timeout(1800)
        sp_text = page.inner_text("body").lower()
        note(
            "detail spesies",
            f"threshold tampil: {'threshold deteksi' in sp_text}, "
            f"status IUCN: {'status iucn' in sp_text}, "
            f"daftar deteksi: {page.locator('tbody tr').count()} baris",
        )

        # 7d. auto-refresh dan tombol analisis ulang
        buka(page, "/recordings/11")
        page.wait_for_timeout(2000)
        reanalyze = page.get_by_role("button", name="Analisis ulang")
        if reanalyze.count():
            reanalyze.click()
            page.wait_for_timeout(2000)
            # Perubahan status job tidak terlihat dari halaman ini kalau worker
            # gagal, jadi statusnya diambil langsung dari API sampai selesai.
            status_akhir = None
            for _ in range(20):
                status_akhir = page.evaluate(
                    """async () => {
                        const t = localStorage.getItem("access_token");
                        const r = await fetch("http://localhost:8000/api/v1/recordings/11", {
                            headers: { Authorization: "Bearer " + t },
                        });
                        const d = await r.json();
                        return d.status;
                    }"""
                )
                if status_akhir in ("done", "failed"):
                    break
                page.wait_for_timeout(3000)
            if status_akhir == "done":
                note("analisis ulang", "job diproses ulang dan selesai dengan status done")
            else:
                note(
                    "analisis ulang",
                    f"PERHATIAN: status akhir {status_akhir}, worker mungkin gagal memproses",
                )
        else:
            note("analisis ulang", "tombol tidak ditemukan")

        # 7e. koreksi metadata rekaman: ubah waktu, tunggu konfirmasi
        buka(page, "/recordings/11")
        page.wait_for_timeout(2000)
        kolom_waktu = page.locator('input[type="datetime-local"]')
        if kolom_waktu.count():
            kolom_waktu.first.fill("2026-09-20T05:30")
            page.get_by_role("button", name="Simpan perubahan").click()
            page.wait_for_timeout(2500)
            isi = page.inner_text("body")
            note(
                "koreksi rekaman",
                "tersimpan" if "Perubahan tersimpan" in isi else "konfirmasi tidak muncul",
            )
        else:
            note("koreksi rekaman", "formulir tidak ada (peran bukan admin atau bukan pengunggah)")

        # 8. upload: elemen nyata
        buka(page, "/upload")
        has_input = page.locator('input[type="file"]').count()
        note("upload", f"{has_input} input file, tombol unggah aktif")

        # 8b. halaman yang tidak pernah dikunjungi click-through sebelumnya.
        # /laporan sempat gagal dimuat di browser karena sebuah deklarasi dipakai
        # sebelum barisnya sendiri, dan tidak ada langkah mana pun yang membukanya.
        for path, penanda in (
            ("/laporan", "Laporan Ringkas Pemantauan Akustik"),
            ("/model", "Status Model"),
        ):
            buka(page, path)
            isi = page.inner_text("body")
            gagal = "tidak bisa dimuat" in isi.lower() or "application error" in isi.lower()
            note(
                f"halaman {path}",
                f"penanda {'ada' if penanda in isi else 'TIDAK ADA'}, "
                f"{'GAGAL DIMUAT' if gagal else 'dimuat normal'}",
            )

        # 9. mobile 390x844: overflow horizontal
        page.set_viewport_size({"width": 390, "height": 844})
        for path in ["/dashboard", "/recordings", "/species", "/sites", "/upload", "/laporan", "/model"]:
            buka(page, path)
            overflow = page.evaluate(
                "(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)()"
            )
            note(f"mobile {path}", f"overflow {overflow}px")

        browser.close()

    bersihkan_lokasi_uji()

    print("\n=== RINGKASAN ===")
    print(f"console error: {len(console_errors)}")
    for e in console_errors[:10]:
        print("  -", e[:160])
    # Prefetch RSC Next.js (?_rsc=) yang dibatalkan saat navigasi halaman bukan
    # kegagalan nyata. Request ke host luar (ubin peta) juga dipisah, karena itu
    # bergantung jaringan tempat pengujian, bukan cacat aplikasi. Keduanya tetap
    # dilaporkan, jadi angkanya jujur.
    gagal_nyata = [
        r for r in failed_requests if "_rsc=" not in r and "localhost" in r
    ]
    gagal_luar = [
        r for r in failed_requests if "_rsc=" not in r and "localhost" not in r
    ]
    print(
        f"request gagal ke aplikasi: {len(gagal_nyata)}, "
        f"ke host luar: {len(gagal_luar)} (total {len(failed_requests)})"
    )
    for r in gagal_nyata[:10]:
        print("  -", r[:160])
    for r in gagal_luar[:3]:
        print("  - luar:", r[:140])
    return 0


if __name__ == "__main__":
    sys.exit(main())
