"""Tambahkan nomor halaman (Times New Roman 11 pt, tengah bawah) mulai halaman 2; cover tanpa nomor.

    <python dengan pymupdf> tambah_nomor.py masuk.pdf keluar.pdf
"""
import sys

import pymupdf

masuk, keluar = sys.argv[1], sys.argv[2]
doc = pymupdf.open(masuk)
for i, hal in enumerate(doc):
    if i == 0:
        continue
    teks = str(i + 1)
    lebar = pymupdf.get_text_length(teks, fontname="tiro", fontsize=11)
    x = (hal.rect.width - lebar) / 2
    y = hal.rect.height - 1.5 * 72 / 2.54  # 1,5 cm dari tepi bawah
    hal.insert_text((x, y), teks, fontname="tiro", fontsize=11, color=(0, 0, 0))
doc.set_metadata({"title": "Proposal GemaHutan - USB 2026 Software Development",
                  "author": "Tim GemaHutan, Universitas Gunadarma", "subject": "Proposal Software Development"})
doc.save(keluar, garbage=3, deflate=True)
print(keluar, doc.page_count, "halaman")
