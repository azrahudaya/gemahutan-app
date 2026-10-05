"""Komposit tangkapan layar tampilan hijau (5 Oktober 2026) untuk Bagian 10 proposal.

    python3 docs/assets/diagram_src/buat_komposit_v2.py

Sumber: docs/assets/screenshots/v2/*.png, diambil dari stack lokal dengan akun uji per peran.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

AKAR = Path(__file__).resolve().parents[3]
SS = AKAR / "docs/assets/screenshots/v2"
OUT = AKAR / "docs/assets/screenshots"


def font(uk):
    for p in ("/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, uk)
    return ImageFont.load_default()


def label(im, teks, tinggi=110):
    k = Image.new("RGB", (im.width, im.height + tinggi), "white")
    k.paste(im, (0, 0))
    d = ImageDraw.Draw(k)
    f = font(int(tinggi * 0.5))
    w = d.textlength(teks, font=f)
    d.text(((im.width - w) / 2, im.height + tinggi * 0.18), teks, font=f, fill="#111111")
    return k


def tepi(im, warna="#A1A1AA", tebal=4):
    k = Image.new("RGB", (im.width + 2 * tebal, im.height + 2 * tebal), warna)
    k.paste(im, (tebal, tebal))
    return k


def tinggi_sama(ims, h):
    return [im.resize((int(im.width * h / im.height), h)) for im in ims]


def lebar_sama(ims, w):
    return [im.resize((w, int(im.height * w / im.width))) for im in ims]


def sejajar(ims, jarak=60):
    h = max(i.height for i in ims)
    k = Image.new("RGB", (sum(i.width for i in ims) + jarak * (len(ims) - 1), h), "white")
    x = 0
    for i in ims:
        k.paste(i, (x, 0))
        x += i.width + jarak
    return k


def tumpuk(ims, jarak=50):
    w = max(i.width for i in ims)
    k = Image.new("RGB", (w, sum(i.height for i in ims) + jarak * (len(ims) - 1)), "white")
    y = 0
    for i in ims:
        k.paste(i, ((w - i.width) // 2, y))
        y += i.height + jarak
    return k


buka = lambda n: Image.open(SS / f"{n}.png").convert("RGB")  # noqa: E731

a, b = tinggi_sama([buka("dasbor"), buka("simulasi")], 1800)
sejajar([label(tepi(a), "(a) Dasbor kawasan (admin dan peneliti)", 120),
         label(tepi(b), "(b) Simulasi perkiraan lokasi dengan tiga alat virtual", 120)]
        ).save(OUT / "v2_dasbor_simulasi.png", dpi=(300, 300))

a, b = tinggi_sama([buka("detail_spektrogram"), buka("detail_deteksi")], 1430)
sejajar([label(tepi(a), "(a) Spektrogram dan indeks soundscape", 110),
         label(tepi(b), "(b) Deteksi dengan tombol verifikasi", 110)]
        ).save(OUT / "v2_detail_rekaman.png", dpi=(300, 300))

ims = tinggi_sama([buka("hp_rekam"), buka("hp_detail"), buka("hp_simulasi")], 2532)
sejajar([label(tepi(ims[0]), "(a) Rekam dari peramban", 130),
         label(tepi(ims[1]), "(b) Hasil rekaman", 130),
         label(tepi(ims[2]), "(c) Simulasi lokasi", 130)]
        ).save(OUT / "v2_ponsel.png", dpi=(300, 300))

for n in ("v2_dasbor_simulasi", "v2_detail_rekaman", "v2_ponsel"):
    im = Image.open(OUT / f"{n}.png")
    if im.width > 3200:
        im.resize((3200, int(im.height * 3200 / im.width))).save(OUT / f"{n}.png", dpi=(300, 300))
    print(n, Image.open(OUT / f"{n}.png").size)
