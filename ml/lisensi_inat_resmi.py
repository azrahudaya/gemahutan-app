"""Cocokkan lisensi tiap klip iNat ke ANOTASI RESMI iNatSounds 2024 (S2/L6-5).

Kenapa bukan API iNaturalist: sudah dicoba dan TIDAK BISA. Endpoint
`/v1/observations/{uuid}` membalas HTTP 422 untuk seluruh 3205 UUID, dan
`?uuid=<uuid>` membalas HTTP 200 dengan `total_results: 0`. Artinya UUID yang
ada di kolom `local_path` bukan ID observasi iNaturalist, jadi tidak ada
pertanyaan yang bisa diajukan ke API itu. Bukti ini dicatat supaya keputusan
tidak diulang.

Jalur yang sah (diminta ML_08 L6-5): berkas anotasi resmi dataset, diunduh dari
AWS Open Data Program sesuai README github.com/visipedia/inat_sounds. Hanya
JSON-nya yang diunduh (18 MB), audio 81 GB tidak perlu:

  train.json.tar.gz  md5 d0ae17ef52078194d450a83b5efe68a4
  val.json.tar.gz    md5 8e6e4b9628d43e36f1fea4621945403a

Setiap entri `audio` di anotasi itu memuat `file_name` yang mengandung UUID
klip DAN `license` berupa id ke tabel `licenses`. Itulah yang dicocokkan.

Keluaran:
  ml/data/manifest_lisensi_inat.csv   bukti per klip
  ml/reports/lisensi_inat_resmi.json  ringkasan
  ml/data/klip_nd_dibuang.json        daftar clip_id ND untuk dikeluarkan

Jalankan: source .venv/bin/activate && python ml/lisensi_inat_resmi.py
"""
from __future__ import annotations

import collections
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"
DATA = ML_DIR / "data"
REPORTS = ML_DIR / "reports"
ANOT_DIR = DATA / "inat_annotations"
MANIFEST_V2 = DATA / "manifest_v2.csv"
MANIFEST_PRODUKSI = DATA / "manifest_latih_produksi.csv"
SPLITS = DATA / "splits_v3.json"

OUT_CSV = DATA / "manifest_lisensi_inat.csv"
OUT_JSON = REPORTS / "lisensi_inat_resmi.json"
OUT_ND = DATA / "klip_nd_dibuang.json"

POLA_UUID = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE
)

# Nama lisensi di anotasi resmi -> kode pendek yang ditulis ke manifest.
# Kode ini yang dibaca ops/audit_model.py C17, jadi varian ND HARUS memuat
# "-nd" supaya ikut tertangkap penyaringnya.
KODE_LISENSI = {
    "Attribution License": "cc-by-4.0",
    "Attribution-NonCommercial License": "cc-by-nc-4.0",
    "Attribution-NonCommercial-NoDerivatives License": "cc-by-nc-nd-4.0",
    "Attribution-NonCommercial-ShareAlike License": "cc-by-nc-sa-4.0",
    "Public Domain Dedication": "cc0-1.0",
    "Attribution-NoDerivatives License": "cc-by-nd-4.0",
    "Attribution-ShareAlike License": "cc-by-sa-4.0",
}


def kode_itu_nd(kode: str) -> bool:
    """ND = No Derivatives. Model adalah karya turunan, jadi ND tidak boleh."""
    return "-nd-" in kode or kode.endswith("-nd")


def peta_uuid_klip() -> dict[str, str]:
    """clip_id -> UUID, diambil dari nama berkas di kolom local_path."""
    peta: dict[str, str] = {}
    if not MANIFEST_V2.exists():
        return peta
    with open(MANIFEST_V2, newline="") as f:
        for r in csv.DictReader(f):
            m = POLA_UUID.search(r.get("local_path", ""))
            if m:
                peta[r["clip_id"]] = m.group(1).lower()
    return peta


def indeks_anotasi() -> tuple[dict[str, tuple[str, str, str]], dict]:
    """UUID -> (nama_lisensi, url, berkas_sumber), plus ringkasan sumber."""
    idx: dict[str, tuple[str, str, str]] = {}
    sumber = {}
    for nama in ("train.json", "val.json"):
        path = ANOT_DIR / nama
        if not path.exists():
            continue
        d = json.loads(path.read_text())
        lisensi = {x["id"]: x for x in d["licenses"]}
        n = 0
        for a in d["audio"]:
            m = POLA_UUID.search(a["file_name"])
            if not m:
                continue
            lic = lisensi[a["license"]]
            idx[m.group(1).lower()] = (lic["name"], lic["url"], nama)
            n += 1
        sumber[nama] = n
    return idx, sumber


def main() -> int:
    if not ANOT_DIR.exists() or not list(ANOT_DIR.glob("*.json")):
        print(f"ERROR: anotasi resmi tidak ada di {ANOT_DIR}")
        print("Unduh dulu train.json.tar.gz dan val.json.tar.gz (lihat docstring).")
        return 1

    uuid_klip = peta_uuid_klip()
    idx, sumber = indeks_anotasi()
    print(f"Klip dengan UUID di manifest_v2: {len(uuid_klip)}")
    print(f"UUID terindeks dari anotasi resmi: {len(idx)} {sumber}")

    baris = []
    tidak_ketemu = []
    for clip_id, uuid in sorted(uuid_klip.items()):
        hit = idx.get(uuid)
        if hit is None:
            tidak_ketemu.append(clip_id)
            baris.append({
                "clip_id": clip_id,
                "inat_uuid": uuid,
                "license": "",
                "license_url": "",
                "nama_lisensi": "",
                "sumber_lisensi": "",
                "status": "tidak_ketemu",
            })
            continue
        nama, url, berkas = hit
        kode = KODE_LISENSI.get(nama, "")
        if not kode:
            # Lisensi baru yang belum dipetakan: jangan diam-diam dianggap aman.
            status = "lisensi_tak_dikenal"
        else:
            status = "dilarang_nd" if kode_itu_nd(kode) else "aman"
        baris.append({
            "clip_id": clip_id,
            "inat_uuid": uuid,
            "license": kode,
            "license_url": url,
            "nama_lisensi": nama,
            "sumber_lisensi": f"anotasi_resmi_inatsounds_2024:{berkas}",
            "status": status,
        })

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "clip_id", "inat_uuid", "license", "license_url",
            "nama_lisensi", "sumber_lisensi", "status",
        ])
        w.writeheader()
        w.writerows(baris)

    per_status = collections.Counter(b["status"] for b in baris)
    per_lisensi = collections.Counter(b["nama_lisensi"] for b in baris if b["nama_lisensi"])
    nd = [b["clip_id"] for b in baris if b["status"] == "dilarang_nd"]
    tak_dikenal = [b["clip_id"] for b in baris if b["status"] == "lisensi_tak_dikenal"]

    # Berapa yang benar-benar menyentuh split latih produksi.
    di_latih_nd = []
    if SPLITS.exists():
        sp = json.loads(SPLITS.read_text())
        latih = set(sp.get("train", [])) | set(sp.get("val", []))
        di_latih_nd = sorted(set(nd) & latih)

    ringkasan = {
        "sumber": "anotasi resmi iNatSounds 2024 (AWS Open Data)",
        "berkas_anotasi": sumber,
        "klip_iNat_diperiksa": len(uuid_klip),
        "cocok": len(uuid_klip) - len(tidak_ketemu),
        "tidak_ketemu": len(tidak_ketemu),
        "per_status": dict(per_status),
        "per_lisensi": dict(per_lisensi),
        "nd_total": len(nd),
        "nd_di_split_latih_produksi": len(di_latih_nd),
        "lisensi_tak_dikenal": len(tak_dikenal),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(ringkasan, indent=2, ensure_ascii=False))
    OUT_ND.write_text(json.dumps({
        "alasan": "lisensi ND (No Derivatives), model adalah karya turunan",
        "sumber": "anotasi_resmi_inatsounds_2024",
        "clip_id": sorted(nd),
        "clip_id_di_split_latih_produksi": di_latih_nd,
    }, indent=2, ensure_ascii=False))

    print(f"\nCocok: {ringkasan['cocok']}/{len(uuid_klip)}, tidak ketemu {len(tidak_ketemu)}")
    for nama, n in per_lisensi.most_common():
        tanda = "  <- ND, dibuang" if kode_itu_nd(KODE_LISENSI.get(nama, "")) else ""
        print(f"  {n:5d}  {nama}{tanda}")
    print(f"\nND total: {len(nd)}, yang masuk split latih produksi: {len(di_latih_nd)}")
    if tak_dikenal:
        print(f"PERINGATAN: {len(tak_dikenal)} klip punya lisensi yang belum dipetakan")
    print(f"\nBukti per klip: {OUT_CSV}")
    print(f"Ringkasan: {OUT_JSON}")
    print(f"Daftar ND: {OUT_ND}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
