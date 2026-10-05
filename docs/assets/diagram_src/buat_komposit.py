"""Gabungkan tangkapan layar menjadi gambar komposit berlabel untuk proposal.

Jalankan dari akar repo setelah docs/assets/screenshots/ terisi:
    python3 docs/assets/diagram_src/buat_komposit.py
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
SS = ROOT / "docs/assets/screenshots"
OUT = ROOT / "docs/assets/screenshots"
FONT = subprocess.run(["fc-match", "-f", "%{file}", "Plus Jakarta Sans"], capture_output=True, text=True).stdout


def f(ukuran, tebal=True):
    fn = ImageFont.truetype(FONT, ukuran)
    try:
        fn.set_variation_by_axes([700 if tebal else 400])
    except (OSError, AttributeError):
        pass
    return fn


def label(im, teks, tinggi_label=110):
    """Tambahkan pita label di bawah gambar."""
    kanvas = Image.new("RGB", (im.width, im.height + tinggi_label), "white")
    kanvas.paste(im, (0, 0))
    d = ImageDraw.Draw(kanvas)
    fn = f(int(tinggi_label * 0.5))
    w = d.textlength(teks, font=fn)
    d.text(((im.width - w) / 2, im.height + tinggi_label * 0.18), teks, font=fn, fill="#09090B")
    return kanvas


def tinggi_sama(ims, h):
    return [im.resize((int(im.width * h / im.height), h), Image.LANCZOS) for im in ims]


def sejajar(ims, jarak=60):
    W = sum(i.width for i in ims) + jarak * (len(ims) - 1)
    H = max(i.height for i in ims)
    k = Image.new("RGB", (W, H), "white")
    x = 0
    for i in ims:
        k.paste(i, (x, 0))
        x += i.width + jarak
    return k


def tumpuk(ims, jarak=50):
    W = max(i.width for i in ims)
    H = sum(i.height for i in ims) + jarak * (len(ims) - 1)
    k = Image.new("RGB", (W, H), "white")
    y = 0
    for i in ims:
        k.paste(i, ((W - i.width) // 2, y))
        y += i.height + jarak
    return k


def tepi(im, warna="#A1A1AA", tebal=4):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width - 1, im.height - 1], outline=warna, width=tebal)
    return im


buka = lambda n: Image.open(SS / f"{n}.png").convert("RGB")  # noqa: E731

# 1. dashboard + peta lokasi
a, b = tinggi_sama([buka("dashboard"), buka("peta_lokasi")], 1800)
k1 = sejajar([label(tepi(a), "(a) Dashboard ringkasan"), label(tepi(b), "(b) Peta lokasi perekaman")])
k1.save(OUT / "komposit_dashboard_peta.png", dpi=(300, 300))

# 2. detail rekaman #12: spektrogram + indeks, lalu tabel deteksi dengan tombol verifikasi
penuh = buka("detail_rekaman_penuh")
atas = penuh.crop((704, 1640, 2688, 2680))
bawah = penuh.crop((672, 3540, 2720, 4380))
k2 = tumpuk([label(tepi(atas), "(a) Spektrogram dan indeks soundscape"),
             label(tepi(bawah), "(b) Deteksi spesies dengan tombol verifikasi ahli")])
k2.save(OUT / "komposit_detail_rekaman.png", dpi=(300, 300))

# 3. unggah batch (desktop) + rekam dan detail (ponsel)
u, m1, m2 = tinggi_sama([buka("unggah"), buka("m_rekam"), buka("m_detail_rekaman")], 1800)
k3 = sejajar([label(tepi(u), "(a) Unggah batch"), label(tepi(m1), "(b) Rekam (ponsel)"),
              label(tepi(m2), "(c) Detail (ponsel)")])
k3.save(OUT / "komposit_unggah_ponsel.png", dpi=(300, 300))
for n in ("komposit_dashboard_peta", "komposit_detail_rekaman", "komposit_unggah_ponsel"):
    im = Image.open(OUT / f"{n}.png")
    print(n, im.size, f"rasio tinggi/lebar {im.height / im.width:.2f}")
