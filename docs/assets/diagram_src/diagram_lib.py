"""Pustaka kecil diagram: satu spesifikasi menghasilkan .drawio dan PNG.

Setiap diagram ditulis sebagai daftar kotak (node), wadah (group), garis (edge),
dan teks lepas. Keluarannya:
  - <nama>.drawio  bisa dibuka dan diedit di draw.io (app.diagrams.net)
  - <nama>.png     render resolusi tinggi dengan tata letak yang sama

Satuan koordinat adalah piksel pada skala 1. PNG dirender pada SKALA kali lipat.
"""
from __future__ import annotations

import html
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

SKALA = 4

# Palet cetak GemaHutan (tema hijau DESIGN.md untuk kertas putih). Nama BIRU dipertahankan
# untuk kompatibilitas; nilainya hijau utama, MINT dipakai sebagai aksen jingga.
TINTA = "#09090B"
GARIS = "#3F3F46"
TEKS2 = "#52525B"
ABU = "#F4F4F5"
ABU_TEPI = "#A1A1AA"
BIRU = "#00873F"
BIRU_MUDA = "#E5F6EC"
MINT = "#FFF4E0"
MINT_TEPI = "#9A5B00"
PUTIH = "#FFFFFF"


def _font_path(pola: str) -> str:
    out = subprocess.run(["fc-match", "-f", "%{file}", pola], capture_output=True, text=True).stdout
    return out.strip()


FONT_REG = _font_path("Plus Jakarta Sans:style=Regular")
FONT_BOLD = _font_path("Plus Jakarta Sans:style=Bold")
FONT_IT = _font_path("Plus Jakarta Sans:style=Italic")


def font(ukuran: float, tebal=False, miring=False):
    """Plus Jakarta Sans terpasang sebagai variable font: ketebalan diatur lewat sumbu wght."""
    path = FONT_IT if miring else FONT_REG
    f = ImageFont.truetype(path, int(round(ukuran * SKALA)))
    try:
        f.set_variation_by_axes([700 if tebal else 400])
    except (OSError, AttributeError):
        pass
    return f


@dataclass
class Node:
    id: str
    x: float
    y: float
    w: float
    h: float
    teks: str                      # baris dipisah "\n"; baris pertama bisa tebal
    isi: str = ABU
    tepi: str = ABU_TEPI
    warna_teks: str = TINTA
    judul_tebal: bool = True
    putus: bool = False            # garis putus-putus (rencana)
    ukuran: float = 12.5
    rata: str = "tengah"          # tengah | kiri
    radius: float = 5


@dataclass
class Grup:
    id: str
    x: float
    y: float
    w: float
    h: float
    judul: str
    isi: str = PUTIH
    tepi: str = ABU_TEPI
    putus: bool = False


@dataclass
class Edge:
    dari: tuple            # (x, y) titik awal
    ke: tuple              # (x, y) titik akhir (ujung panah)
    via: list = field(default_factory=list)
    label: str = ""
    label_pos: tuple | None = None
    warna: str = GARIS
    putus: bool = False
    panah: bool = True
    src: str | None = None  # id node untuk drawio (opsional)
    dst: str | None = None


@dataclass
class Teks:
    x: float
    y: float
    teks: str
    ukuran: float = 11
    warna: str = TEKS2
    tebal: bool = False
    miring: bool = False
    rata: str = "kiri"


@dataclass
class Diagram:
    nama: str
    lebar: float
    tinggi: float
    grup: list = field(default_factory=list)
    node: list = field(default_factory=list)
    edge: list = field(default_factory=list)
    teks: list = field(default_factory=list)

    # ------------------------------------------------------------------ PNG
    def _s(self, v):
        return int(round(v * SKALA))

    def _teks_kotak(self, d, n: Node):
        baris = n.teks.split("\n")
        f_judul = font(n.ukuran, tebal=n.judul_tebal)
        f_isi = font(n.ukuran - 1.5)
        tinggi_baris = []
        for i, b in enumerate(baris):
            f = f_judul if i == 0 else f_isi
            tinggi_baris.append((b, f, (n.ukuran if i == 0 else n.ukuran - 1.5) * 1.32))
        total = sum(t for _, _, t in tinggi_baris)
        y = n.y + (n.h - total) / 2
        for b, f, t in tinggi_baris:
            lebar_teks = d.textlength(b, font=f) / SKALA
            if n.rata == "tengah":
                x = n.x + (n.w - lebar_teks) / 2
            else:
                x = n.x + 8
            d.text((self._s(x), self._s(y + t * 0.12)), b, font=f, fill=n.warna_teks)
            y += t

    def _garis_putus(self, d, p1, p2, warna, lebar, pola=(6, 4)):
        import math
        (x1, y1), (x2, y2) = p1, p2
        panjang = math.hypot(x2 - x1, y2 - y1)
        if panjang == 0:
            return
        dx, dy = (x2 - x1) / panjang, (y2 - y1) / panjang
        pos, nyala = 0.0, True
        while pos < panjang:
            seg = pola[0] if nyala else pola[1]
            akhir = min(pos + seg * SKALA / SKALA, panjang)
            if nyala:
                d.line([(x1 + dx * pos, y1 + dy * pos), (x1 + dx * akhir, y1 + dy * akhir)], fill=warna, width=lebar)
            pos, nyala = akhir, not nyala

    def _kotak(self, d, x, y, w, h, isi, tepi, putus, radius, lebar=1.4):
        kotak = [self._s(x), self._s(y), self._s(x + w), self._s(y + h)]
        if putus:
            d.rounded_rectangle(kotak, radius=self._s(radius), fill=isi)
            L = self._s(lebar)
            pts = [(kotak[0], kotak[1]), (kotak[2], kotak[1]), (kotak[2], kotak[3]), (kotak[0], kotak[3]), (kotak[0], kotak[1])]
            for a, b in zip(pts, pts[1:], strict=False):
                self._garis_putus(d, a, b, tepi, L, pola=(self._s(5), self._s(3.5)))
        else:
            d.rounded_rectangle(kotak, radius=self._s(radius), fill=isi, outline=tepi, width=self._s(lebar))

    def _panah(self, d, e: Edge):
        import math
        pts = [e.dari, *e.via, e.ke]
        P = [(self._s(x), self._s(y)) for x, y in pts]
        L = self._s(1.5)
        for a, b in zip(P, P[1:], strict=False):
            if e.putus:
                self._garis_putus(d, a, b, e.warna, L, pola=(self._s(5), self._s(3.5)))
            else:
                d.line([a, b], fill=e.warna, width=L)
        if e.panah:
            (x1, y1), (x2, y2) = P[-2], P[-1]
            ang = math.atan2(y2 - y1, x2 - x1)
            ukuran = self._s(7)
            kiri = (x2 - ukuran * math.cos(ang - 0.42), y2 - ukuran * math.sin(ang - 0.42))
            kanan = (x2 - ukuran * math.cos(ang + 0.42), y2 - ukuran * math.sin(ang + 0.42))
            d.polygon([(x2, y2), kiri, kanan], fill=e.warna)
        if e.label:
            if e.label_pos:
                lx, ly = e.label_pos
            else:
                # tengah segmen terpanjang
                seg = max(zip(pts, pts[1:], strict=False), key=lambda s: abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))
                lx, ly = (seg[0][0] + seg[1][0]) / 2, (seg[0][1] + seg[1][1]) / 2
            f = font(10.5, miring=True)
            baris = e.label.split("\n")
            lebar_maks = max(d.textlength(b, font=f) for b in baris) / SKALA
            tinggi = 13.5 * len(baris)
            d.rectangle([self._s(lx - lebar_maks / 2 - 3), self._s(ly - tinggi / 2 - 1),
                         self._s(lx + lebar_maks / 2 + 3), self._s(ly + tinggi / 2 + 1)], fill=PUTIH)
            for i, b in enumerate(baris):
                w = d.textlength(b, font=f) / SKALA
                d.text((self._s(lx - w / 2), self._s(ly - tinggi / 2 + i * 13.5 + 1)), b, font=f, fill=TEKS2)

    def render_png(self, path: Path):
        im = Image.new("RGB", (self._s(self.lebar), self._s(self.tinggi)), PUTIH)
        d = ImageDraw.Draw(im)
        for g in self.grup:
            self._kotak(d, g.x, g.y, g.w, g.h, g.isi, g.tepi, g.putus, 7)
            d.text((self._s(g.x + 10), self._s(g.y + 7)), g.judul, font=font(11.5, tebal=True), fill=TEKS2)
        for e in self.edge:
            self._panah(d, e)
        for n in self.node:
            self._kotak(d, n.x, n.y, n.w, n.h, n.isi, n.tepi, n.putus, n.radius)
            self._teks_kotak(d, n)
        for t in self.teks:
            f = font(t.ukuran, tebal=t.tebal, miring=t.miring)
            for i, b in enumerate(t.teks.split("\n")):
                w = d.textlength(b, font=f) / SKALA
                x = t.x if t.rata == "kiri" else (t.x - w / 2 if t.rata == "tengah" else t.x - w)
                d.text((self._s(x), self._s(t.y + i * t.ukuran * 1.35)), b, font=f, fill=t.warna)
        im.save(path, dpi=(300, 300))

    # --------------------------------------------------------------- drawio
    def render_drawio(self, path: Path):
        sel = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
        fam = "fontFamily=Plus Jakarta Sans;"
        for g in self.grup:
            gaya = (f"rounded=1;arcSize=3;whiteSpace=wrap;html=1;fillColor={g.isi};strokeColor={g.tepi};"
                    f"verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontStyle=1;fontSize=11;"
                    f"fontColor={TEKS2};{fam}" + ("dashed=1;" if g.putus else ""))
            sel.append(f'<mxCell id="{g.id}" value="{escape(g.judul, {chr(34): "&quot;"})}" style="{gaya}" vertex="1" parent="1">'
                       f'<mxGeometry x="{g.x}" y="{g.y}" width="{g.w}" height="{g.h}" as="geometry"/></mxCell>')
        for n in self.node:
            baris = n.teks.split("\n")
            nilai = (f"<b>{html.escape(baris[0])}</b>" if n.judul_tebal else html.escape(baris[0]))
            if len(baris) > 1:
                nilai += "<br>" + "<br>".join(f'<font style="font-size:{n.ukuran - 1.5}px">{html.escape(b)}</font>' for b in baris[1:])
            gaya = (f"rounded=1;arcSize={max(3, int(n.radius / min(n.w, n.h) * 100))};whiteSpace=wrap;html=1;"
                    f"fillColor={n.isi};strokeColor={n.tepi};fontColor={n.warna_teks};fontSize={n.ukuran};{fam}"
                    + ("dashed=1;" if n.putus else "") + ("align=left;spacingLeft=8;" if n.rata == "kiri" else ""))
            sel.append(f'<mxCell id="{n.id}" value="{html.escape(nilai)}" style="{gaya}" vertex="1" parent="1">'
                       f'<mxGeometry x="{n.x}" y="{n.y}" width="{n.w}" height="{n.h}" as="geometry"/></mxCell>')
        for i, e in enumerate(self.edge):
            gaya = (f"edgeStyle=none;html=1;rounded=0;strokeWidth=1.5;strokeColor={e.warna};fontSize=10;"
                    f"fontStyle=2;fontColor={TEKS2};{fam}" + ("dashed=1;" if e.putus else "")
                    + ("endArrow=block;endFill=1;" if e.panah else "endArrow=none;"))
            titik = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in e.via)
            sel.append(f'<mxCell id="e{i}" value="{html.escape(e.label).replace(chr(10), "&lt;br&gt;")}" style="{gaya}" edge="1" parent="1">'
                       f'<mxGeometry relative="1" as="geometry">'
                       f'<mxPoint x="{e.dari[0]}" y="{e.dari[1]}" as="sourcePoint"/>'
                       f'<mxPoint x="{e.ke[0]}" y="{e.ke[1]}" as="targetPoint"/>'
                       + (f'<Array as="points">{titik}</Array>' if e.via else "") + '</mxGeometry></mxCell>')
        for i, t in enumerate(self.teks):
            gaya = (f"text;html=1;align={'left' if t.rata == 'kiri' else ('center' if t.rata == 'tengah' else 'right')};"
                    f"verticalAlign=top;fontSize={t.ukuran};fontColor={t.warna};{fam}"
                    + ("fontStyle=1;" if t.tebal else ("fontStyle=2;" if t.miring else "")))
            lebar = 700
            x = t.x if t.rata == "kiri" else (t.x - lebar / 2 if t.rata == "tengah" else t.x - lebar)
            sel.append(f'<mxCell id="t{i}" value="{html.escape(t.teks).replace(chr(10), "&lt;br&gt;")}" style="{gaya}" vertex="1" parent="1">'
                       f'<mxGeometry x="{x}" y="{t.y}" width="{lebar}" height="{t.ukuran * 1.4 * (t.teks.count(chr(10)) + 1)}" as="geometry"/></mxCell>')
        xml = ('<mxfile host="gemahutan-diagram-lib"><diagram id="d1" name="' + self.nama + '">'
               f'<mxGraphModel dx="{self.lebar}" dy="{self.tinggi}" grid="1" gridSize="10" guides="1" tooltips="1" '
               f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{int(self.lebar)}" '
               f'pageHeight="{int(self.tinggi)}" math="0" shadow="0"><root>' + "".join(sel)
               + '</root></mxGraphModel></diagram></mxfile>')
        path.write_text(xml, encoding="utf-8")

    def simpan(self, folder: Path):
        folder.mkdir(parents=True, exist_ok=True)
        self.render_png(folder / f"{self.nama}.png")
        self.render_drawio(folder / f"{self.nama}.drawio")
        return folder / f"{self.nama}.png"
