"""Pratinjau PDF: blok isi yang sama dirender ke HTML A4 lalu dicetak Chromium.

Dipakai untuk memperkirakan jumlah halaman dan memeriksa tata letak karena
LibreOffice tidak terpasang. Tinggi baris 1,5 spasi Word untuk Times New Roman
12 pt kira-kira 1,725 x ukuran huruf, jadi CSS memakai line-height 1.725.
"""
import html
from pathlib import Path

from render import potong

CSS = """
@page { size: A4; margin: 2.5cm; }
body { font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.725; margin: 0; }
p { margin: 0 0 3pt 0; text-align: justify; }
p.i { text-indent: 1cm; }
h1, h2 { font-size: 12pt; margin: 12pt 0 4pt 0; line-height: 1.725; break-after: avoid; }
h2 { margin-top: 8pt; }
ul { margin: 0 0 2pt 0; padding-left: 0.9cm; } li { text-align: justify; margin-bottom: 1pt; }
ol { margin: 0 0 2pt 0; padding-left: 0.75cm; }
table { break-inside: avoid; border-collapse: collapse; margin: 0 auto 8pt auto; font-size: 10.5pt; line-height: 1.15; }
td, th { border: 0.6pt solid #000; padding: 1.5pt 4pt; vertical-align: top; text-align: left; }
th { background: #E4E4E7; }
.cap { font-size: 11pt; text-align: center; margin-bottom: 8pt; break-before: avoid; }
.tcap { font-size: 11pt; text-align: justify; margin-top: 6pt; break-after: avoid; }
figure { margin: 6pt 0 0 0; text-align: center; break-inside: avoid; }
.hl { background: #FFFF00; }
pre { font-family: 'Courier New', monospace; font-size: 10pt; line-height: 1.2; margin: 0 0 4pt 1cm; }
.ref { padding-left: 1cm; text-indent: -1cm; text-align: left; line-height: 1.3; margin-bottom: 4pt; }
.cover p { text-align: center; }
.pb { break-after: page; }
.eq { display: flex; align-items: center; margin: 2pt 0 4pt 0; }
.eq span.r { flex: 1; text-align: center; } .eq span.n { width: 1.2cm; text-align: right; }
"""


def _sebaris(teks):
    out = []
    for t, g in potong(teks):
        t = html.escape(t)
        out.append({"b": f"<b>{t}</b>", "i": f"<i>{t}</i>", "h": f'<span class="hl">{t}</span>'}.get(g, t))
    return "".join(out)


def ke_html(blok, akar: Path) -> str:
    o = [f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"]
    ng = nt = 0
    for b in blok:
        j = b[0]
        if j == "cover":
            o.append('<div class="cover">')
            for teks, uk, tebal, spasi in b[1]["baris"]:
                if teks == "LOGO":
                    o.append(f'<p><img src="file://{akar / b[1]["logo"]}" style="width:4.2cm"></p>')
                elif teks.startswith("IMG:"):
                    rel, lebar = teks[4:].split("|")
                    o.append(f'<p style="margin-bottom:{spasi}pt"><img src="file://{akar / rel}" style="width:{lebar}cm"></p>')
                else:
                    w = "bold" if tebal else "normal"
                    o.append(f'<p style="font-size:{uk or 12}pt;font-weight:{w};margin-bottom:{spasi}pt">{_sebaris(teks)}</p>')
            o.append("</div>")
        elif j in ("h1", "h2"):
            o.append(f"<{j}>{html.escape(b[1])}</{j}>")
        elif j in ("p", "p0"):
            o.append(f'<p class="{"i" if j == "p" else ""}">{_sebaris(b[1])}</p>')
        elif j == "bul":
            o.append("<ul>" + "".join(f"<li>{_sebaris(x)}</li>" for x in b[1]) + "</ul>")
        elif j == "num":
            o.append("<ol>" + "".join(f"<li>{_sebaris(x)}</li>" for x in b[1]) + "</ol>")
        elif j == "eq":
            o.append(f'<div class="eq"><span class="r">{_sebaris(b[1])}</span><span class="n">({b[2]})</span></div>')
        elif j == "kode":
            o.append("<pre>" + html.escape("\n".join(b[1])) + "</pre>")
        elif j == "tbl":
            _, judul, header, baris, lebar = b
            nt += 1
            o.append(f'<p class="tcap">Tabel {nt}. {_sebaris(judul)}</p><table>')
            o.append("<tr>" + "".join(f'<th style="width:{w}cm">{_sebaris(h)}</th>' for h, w in zip(header, lebar, strict=True)) + "</tr>")
            for r in baris:
                o.append("<tr>" + "".join(f"<td>{_sebaris(c)}</td>" for c in r) + "</tr>")
            o.append("</table>")
        elif j == "fig":
            _, rel, lebar, ket = b
            ng += 1
            o.append(f'<figure><img src="file://{akar / rel}" style="width:{lebar}cm"></figure>'
                     f'<p class="cap">Gambar {ng}. {_sebaris(ket)}</p>')
        elif j == "refs":
            o.append("".join(f'<p class="ref">{_sebaris(r)}</p>' for r in b[1]))
        elif j == "pb":
            o.append('<div class="pb"></div>')
    o.append("</body></html>")
    return "\n".join(o)


def ke_pdf(html_teks: str, html_path: Path, pdf_path: Path):
    from playwright.sync_api import sync_playwright
    html_path.write_text(html_teks, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(f"file://{html_path}", wait_until="load")
        pg.pdf(path=str(pdf_path), format="A4", prefer_css_page_size=True, print_background=True,
               display_header_footer=True, header_template="<span></span>",
               footer_template='<div style="font-size:10pt;width:100%;text-align:center;font-family:Times New Roman">'
                               '<span class="pageNumber"></span></div>',
               margin={"top": "2.5cm", "bottom": "2.5cm", "left": "2.5cm", "right": "2.5cm"})
        b.close()


def ke_pdf_final(html_teks: str, html_path: Path, pdf_path: Path):
    """PDF tanpa nomor halaman bawaan Chromium; nomor ditambah tambah_nomor.py mulai halaman 2."""
    from playwright.sync_api import sync_playwright
    html_path.write_text(html_teks, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(f"file://{html_path}", wait_until="load")
        pg.pdf(path=str(pdf_path), format="A4", prefer_css_page_size=True, print_background=True,
               margin={"top": "2.5cm", "bottom": "2.5cm", "left": "2.5cm", "right": "2.5cm"})
        b.close()
