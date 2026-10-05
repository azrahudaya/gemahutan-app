"""Bangun docs/proposal-usb-v2.docx (dan pratinjau PDF bila diminta).

    python3 docs/assets/proposal_src/buat_proposal.py            # hanya .docx
    python3 docs/assets/proposal_src/buat_proposal.py --pratinjau <folder>
    python3 docs/assets/proposal_src/buat_proposal.py --pdf-mentah <berkas.pdf>   # lalu tambah_nomor.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import isi_1  # noqa: E402
import isi_2  # noqa: E402
import isi_3  # noqa: E402
from data import AKAR, kumpulkan  # noqa: E402
from render import ke_docx  # noqa: E402

f = kumpulkan()
blok = isi_1.isi(f) + isi_2.isi(f) + isi_3.isi(f)
keluaran = AKAR / "docs/proposal-usb-v2.docx"
ng, nt = ke_docx(blok, keluaran, AKAR)
print(f"docx: {keluaran} ({ng} gambar, {nt} tabel)")

if "--pdf-mentah" in sys.argv:
    from render_html import ke_html, ke_pdf_final
    tujuan = Path(sys.argv[sys.argv.index("--pdf-mentah") + 1])
    ke_pdf_final(ke_html(blok, AKAR), tujuan.with_suffix(".html"), tujuan)
    print(f"pdf mentah: {tujuan}")

if "--pratinjau" in sys.argv:
    from render_html import ke_html, ke_pdf
    folder = Path(sys.argv[sys.argv.index("--pratinjau") + 1])
    folder.mkdir(parents=True, exist_ok=True)
    ke_pdf(ke_html(blok, AKAR), folder / "pratinjau.html", folder / "pratinjau.pdf")
    print(f"pratinjau: {folder / 'pratinjau.pdf'}")
