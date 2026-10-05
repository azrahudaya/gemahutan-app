"""Gambar ikon PWA GemaHutan dengan Pillow.

Motif: tiga busur gelombang suara tipis yang memancar dari satu titik, di atas
latar hijau hutan gelap. Motif ini sama dengan penanda identitas di DESIGN.md
(garis gelombang suara tipis), bukan clipart acak, dan tetap terbaca di ukuran
16 piksel karena hanya memakai busur tebal seragam.

Jalankan: python3 ops/make_icons.py
Menghasilkan:
  apps/web/public/favicon.ico
  apps/web/public/apple-touch-icon.png
  apps/web/public/icon-192.png
  apps/web/public/icon-512.png
  apps/web/public/icon-maskable-512.png
"""
from pathlib import Path

from PIL import Image, ImageDraw

PUBLIC = Path(__file__).resolve().parents[1] / "apps" / "web" / "public"

# Latar hijau hutan gelap, satu tingkat di atas shell #09090B supaya ikon punya
# identitas hutan tapi tidak menyilaukan di deretan ikon perangkat.
LATAR = (11, 46, 34, 255)
LATAR_TEPI = (7, 30, 22, 255)
GELOMBANG = (153, 255, 228, 255)  # mint, token --accent
TITIK = (255, 199, 153, 255)      # highlight, token --highlight


def _gambar(ukuran: int, maskable: bool) -> Image.Image:
    # Digambar 4 kali lalu diperkecil, supaya busurnya halus tanpa anti-alias manual.
    skala = 4
    S = ukuran * skala
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    radius = int(S * 0.22)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=radius, fill=LATAR)
    # Lapisan tepi tipis memberi kedalaman tanpa gradien merek.
    d.rounded_rectangle(
        [0, 0, S - 1, S - 1], radius=radius, outline=LATAR_TEPI, width=max(1, S // 96)
    )

    # Zona aman maskable: isi ikon dijaga di dalam 78 persen tengah.
    faktor = 0.62 if maskable else 0.80
    lebar_busur = max(2, int(S * (0.035 if maskable else 0.045)))

    pusat_x = S * 0.30
    pusat_y = S * 0.52
    garis_tengah = S * 0.22

    for i, jari in enumerate((0.34, 0.62, 0.95)):
        jari_px = garis_tengah + S * 0.20 * jari * (faktor / 0.80)
        kotak = [
            pusat_x - jari_px,
            pusat_y - jari_px,
            pusat_x + jari_px,
            pusat_y + jari_px,
        ]
        # Busur dibuka 78 derajat mengarah ke kanan, celahnya kecil supaya tetap
        # terbaca sebagai gelombang suara, bukan huruf C.
        ketebalan = lebar_busur if i < 2 else int(lebar_busur * 0.8)
        d.arc(kotak, start=-39, end=39, fill=GELOMBANG, width=ketebalan)

    # Sumber suara: satu titik penuh di ujung kiri busur.
    r = max(2, int(S * (0.035 if maskable else 0.045)))
    d.ellipse([pusat_x - r, pusat_y - r, pusat_x + r, pusat_y + r], fill=TITIK)

    return img.resize((ukuran, ukuran), Image.LANCZOS)


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)

    _gambar(192, maskable=False).save(PUBLIC / "icon-192.png")
    _gambar(512, maskable=False).save(PUBLIC / "icon-512.png")
    _gambar(512, maskable=True).save(PUBLIC / "icon-maskable-512.png")
    _gambar(180, maskable=False).save(PUBLIC / "apple-touch-icon.png")

    favicon = _gambar(256, maskable=False)
    favicon.save(
        PUBLIC / "favicon.ico",
        sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
    )

    for nama in (
        "favicon.ico",
        "apple-touch-icon.png",
        "icon-192.png",
        "icon-512.png",
        "icon-maskable-512.png",
    ):
        berkas = PUBLIC / nama
        print(f"{nama}: {berkas.stat().st_size} bita")


if __name__ == "__main__":
    main()
