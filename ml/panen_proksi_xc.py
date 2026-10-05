"""Panen metadata rekaman panjang Xeno-canto Indonesia untuk proksi C21 (S7).

Kenapa skrip ini ada, padahal sudah ada ml/extract_xc_indonesia.py: skrip itu
TIDAK BISA dipakai dan angkanya tidak pernah ada. Tiga kesalahannya:

1. Menembak host `api.xeno-canto.org` yang tidak punya catatan DNS. Itu sebab
   sebenarnya dari "DNS resolution failed" yang dicatat sesi sebelumnya, bukan
   jaringan yang mati. Host yang benar `xeno-canto.org`.
2. Daftar TARGET_SPECIES-nya bukan spesies proyek ini. Isinya memuat
   Haliaeetus leucocephalus (elang Amerika Utara), Psittacula echo (Mauritius),
   Leucosarcia picata (Australia), dan `Bucerotidae` yang itu nama famili,
   bukan spesies. 25 spesies yang benar ada di ml/checkpoints/label_map.json.
3. Tidak mengirim kunci API, tidak menyaring lisensi ND, dan tidak membuang ID
   yang sudah terpakai di manifest lain.

Yang dikerjakan di sini sesuai ML_08 B8-proksi:
- Query `cnt:indonesia grp:birds len:60-9999`, hanya lisensi non-ND.
- BUANG setiap ID yang sudah ada di manifest mana pun (latih, uji, lapangan,
  pembagian_openset), supaya set proksi tidak tumpang tindih dengan data latih
  atau data uji.
- Pilih 45 sampai 60 menit dari minimal 3 bioregion dan minimal 10 perekam.
- Cetak sha256 daftar ID terpilih supaya pilihannya bisa diaudit.

Set ini HANYA untuk dilaporkan. Dilarang dipakai memilih ambang, fitur, atau
hiperparameter apa pun (aturan ML_08: keputusan hanya dari bagian pilih dan CV).

Keluaran:
  ml/data/proksi_xc/kandidat.json   seluruh kandidat non-ND setelah penyaringan
  ml/data/proksi_xc/terpilih.json   subset terpilih + sha256 daftar ID
  ml/reports/proksi_xc_panen.md     ringkasan yang bisa dibaca manusia

Jalankan: source .venv/bin/activate && python ml/panen_proksi_xc.py
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"
DATA = ML_DIR / "data"
REPORTS = ML_DIR / "reports"
OUT_DIR = DATA / "proksi_xc"

XC_API = "https://xeno-canto.org/api/3/recordings"
DELAY_S = 1.1

TARGET_MENIT_MIN = 45
TARGET_MENIT_MAKS = 60
MIN_BIOREGION = 3
MIN_PEREKAM = 10
# Satu perekam tidak boleh mendominasi set proksi.
MAKS_PER_PEREKAM = 4

# Kotak lintang/bujur kasar per bioregion Indonesia. Dipakai hanya untuk
# memastikan sebarannya tidak menumpuk di satu pulau; bukan klaim biogeografi.
BIOREGION_KOTAK = [
    ("Sumatra", -6.0, 6.5, 94.0, 107.0),
    ("Jawa-Bali", -9.2, -5.8, 105.0, 115.8),
    ("Kalimantan", -4.5, 7.5, 108.0, 119.5),
    ("Sulawesi", -6.5, 2.5, 118.0, 125.5),
    ("Nusa Tenggara", -11.5, -7.8, 115.5, 125.5),
    ("Maluku", -8.5, 3.0, 125.5, 135.0),
    ("Papua", -9.5, 0.5, 130.0, 141.5),
]
# Kata kunci di kolom `loc` sebagai cadangan kalau koordinatnya kosong.
BIOREGION_KATA = {
    "Sumatra": ("sumatra", "sumatera", "aceh", "riau", "jambi", "lampung", "bengkulu", "palembang"),
    "Jawa-Bali": ("java", "jawa", "bali", "jakarta", "bandung", "yogyakarta", "semarang", "surabaya"),
    "Kalimantan": ("kalimantan", "borneo", "pontianak", "banjarmasin", "samarinda"),
    "Sulawesi": ("sulawesi", "celebes", "makassar", "manado", "kolaka", "palu"),
    "Nusa Tenggara": ("nusa tenggara", "flores", "sumba", "lombok", "timor", "komodo", "alor"),
    "Maluku": ("maluku", "moluccas", "halmahera", "seram", "buru", "ambon", "ternate"),
    "Papua": ("papua", "irian", "jayapura", "raja ampat", "sorong", "merauke"),
}


def lisensi_itu_nd(lic: str) -> bool:
    """True kalau lisensi memuat ND (No Derivatives).

    JEBAKAN yang sudah terbukti memakan 135 dari 194 klip: URL lisensi
    Xeno-canto berakhir dengan garis miring, jadi `lic.split("/")[-1]`
    mengembalikan string KOSONG dan cc-by-nc-nd lolos penyaringan. Di sini
    garis miring di ujung dibuang dulu, lalu kalau segmen terakhir ternyata
    nomor versi (`4.0`) diambil segmen sebelumnya, baru dicek token `nd`.
    """
    if not lic:
        # Tanpa lisensi = tidak boleh dipakai.
        return True
    s = lic.strip().lower().rstrip("/")
    if not s:
        return True
    segmen = [x for x in s.split("/") if x]
    kode = segmen[-1] if segmen else ""
    if re.fullmatch(r"\d+\.\d+", kode) and len(segmen) >= 2:
        kode = segmen[-2]
    token = kode.replace("-", " ").split()
    return "nd" in token


def durasi_ke_detik(length: str) -> float:
    """`1:39` atau `12:03` jadi detik. Format tak terbaca jadi 0."""
    if not length:
        return 0.0
    bagian = str(length).strip().split(":")
    try:
        angka = [float(x) for x in bagian]
    except ValueError:
        return 0.0
    detik = 0.0
    for x in angka:
        detik = detik * 60 + x
    return detik


def bioregion(lat, lng, loc: str) -> str:
    try:
        la = float(lat)
        lo = float(lng)
    except (TypeError, ValueError):
        la = lo = None
    if la is not None and lo is not None:
        for nama, la0, la1, lo0, lo1 in BIOREGION_KOTAK:
            if la0 <= la <= la1 and lo0 <= lo <= lo1:
                return nama
    teks = (loc or "").lower()
    for nama, kata in BIOREGION_KATA.items():
        if any(k in teks for k in kata):
            return nama
    return "tidak diketahui"


def id_sudah_terpakai() -> set[str]:
    """Seluruh ID Xeno-canto yang sudah muncul di manifest mana pun.

    Tanpa ini, set proksi bisa memuat rekaman yang sudah ada di data latih
    (angka jadi optimistis palsu) atau di data uji (merusak kemurnian uji).
    """
    terpakai: set[str] = set()
    pola = re.compile(r"xc-(\d+)", re.IGNORECASE)

    for rel in ("manifest_v2.csv", "field/manifest.csv",
                "uji_independen/manifest.csv", "kelas_langka/manifest.csv"):
        path = DATA / rel
        if not path.exists():
            continue
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                for nilai in (r.get("clip_id", ""), r.get("source_url", ""),
                              r.get("local_path", "")):
                    for m in pola.finditer(str(nilai)):
                        terpakai.add(m.group(1))

    pembagian = DATA / "pembagian_openset.json"
    if pembagian.exists():
        teks = pembagian.read_text()
        for m in pola.finditer(teks):
            terpakai.add(m.group(1))

    return terpakai


def ambil_halaman(page: int, kunci: str) -> dict | None:
    q = urllib.parse.quote("cnt:indonesia grp:birds len:60-9999")
    url = f"{XC_API}?query={q}&per_page=100&page={page}&key={kunci}"
    req = urllib.request.Request(url, headers={"User-Agent": "GemaHutan/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  halaman {page} gagal: {str(e)[:160]}")
        return None


def main() -> int:
    kunci = os.environ.get("XC_API_KEY", "").strip()
    if not kunci:
        env = ROOT / ".env"
        if env.exists():
            for baris in env.read_text().splitlines():
                if baris.startswith("XC_API_KEY"):
                    kunci = baris.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not kunci:
        print("ERROR: XC_API_KEY tidak ada di environment maupun .env")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    terpakai = id_sudah_terpakai()
    print(f"ID Xeno-canto yang sudah terpakai di manifest lain: {len(terpakai)}")

    pertama = ambil_halaman(1, kunci)
    if pertama is None:
        print("ERROR: halaman pertama gagal, hentikan.")
        return 1
    total_halaman = int(pertama.get("numPages", 1))
    print(f"numRecordings {pertama.get('numRecordings')}, numPages {total_halaman}")

    mentah = list(pertama.get("recordings", []))
    for page in range(2, total_halaman + 1):
        time.sleep(DELAY_S)
        d = ambil_halaman(page, kunci)
        if d is None:
            # HTTP 400 = halaman di luar jangkauan; berhenti, jangan diulang.
            break
        recs = d.get("recordings", [])
        if not recs:
            break
        mentah.extend(recs)
        if page % 5 == 0:
            print(f"  halaman {page}/{total_halaman}, terkumpul {len(mentah)}")

    print(f"Total rekaman terkumpul: {len(mentah)}")

    # Penyaringan
    buang = collections.Counter()
    kandidat = []
    for r in mentah:
        rid = str(r.get("id", ""))
        if not rid:
            buang["tanpa id"] += 1
            continue
        if rid in terpakai:
            buang["sudah dipakai manifest lain"] += 1
            continue
        if lisensi_itu_nd(r.get("lic", "")):
            buang["lisensi ND atau kosong"] += 1
            continue
        detik = durasi_ke_detik(r.get("length", ""))
        if detik < 60:
            buang["lebih pendek dari 60 detik"] += 1
            continue
        perekam = (r.get("rec") or "").strip()
        if not perekam:
            buang["tanpa nama perekam"] += 1
            continue
        kandidat.append({
            "id": rid,
            "spesies": f"{r.get('gen','')} {r.get('sp','')}".strip(),
            "nama_umum": r.get("en", ""),
            "perekam": perekam,
            "lisensi": r.get("lic", ""),
            "kualitas": r.get("q", ""),
            "lokasi": r.get("loc", ""),
            "lat": r.get("lat"),
            "lng": r.get("lng"),
            "durasi_s": round(detik, 1),
            "bioregion": bioregion(r.get("lat"), r.get("lng"), r.get("loc", "")),
            "also": r.get("also", []),
            "unduh": r.get("file", f"https://xeno-canto.org/{rid}/download"),
        })

    print("\nDibuang:")
    for k, n in buang.most_common():
        print(f"  {n:5d}  {k}")
    print(f"Kandidat lolos: {len(kandidat)}")

    (OUT_DIR / "kandidat.json").write_text(
        json.dumps(kandidat, indent=2, ensure_ascii=False))

    # Pemilihan: sebar antar bioregion dan perekam, berhenti di 45-60 menit.
    # Diurutkan deterministik supaya pilihannya bisa diulang persis.
    per_region = collections.defaultdict(list)
    for k in kandidat:
        per_region[k["bioregion"]].append(k)
    for v in per_region.values():
        v.sort(key=lambda x: (x["perekam"], int(x["id"])))

    urutan_region = sorted(per_region, key=lambda r: (r == "tidak diketahui", r))
    terpilih: list[dict] = []
    per_perekam = collections.Counter()
    total_detik = 0.0
    maks_detik = TARGET_MENIT_MAKS * 60

    # Ronde round-robin antar bioregion supaya tidak menumpuk di satu pulau.
    idx = {r: 0 for r in urutan_region}
    while total_detik < maks_detik:
        maju = False
        for region in urutan_region:
            if total_detik >= maks_detik:
                break
            daftar = per_region[region]
            while idx[region] < len(daftar):
                kand = daftar[idx[region]]
                idx[region] += 1
                if per_perekam[kand["perekam"]] >= MAKS_PER_PEREKAM:
                    continue
                if total_detik + kand["durasi_s"] > maks_detik:
                    continue
                terpilih.append(kand)
                per_perekam[kand["perekam"]] += 1
                total_detik += kand["durasi_s"]
                maju = True
                break
        if not maju:
            break

    # "tidak diketahui" BUKAN bioregion. Kalau ikut dihitung, klaim cakupan
    # jadi melebihi bukti (8 terdengar lebih banyak dari 7 yang benar-benar
    # teridentifikasi), dan syarat minimal bisa lulus hanya karena koordinat
    # yang kosong.
    region_terpakai = sorted(
        {k["bioregion"] for k in terpilih} - {"tidak diketahui"}
    )
    n_region_tak_diketahui = sum(
        1 for k in terpilih if k["bioregion"] == "tidak diketahui"
    )
    menit = total_detik / 60
    daftar_id = sorted((k["id"] for k in terpilih), key=int)
    sha = hashlib.sha256("\n".join(daftar_id).encode("utf-8")).hexdigest()

    syarat = {
        "menit_45_sampai_60": TARGET_MENIT_MIN <= menit <= TARGET_MENIT_MAKS,
        "bioregion_min_3": len(region_terpakai) >= MIN_BIOREGION,
        "perekam_min_10": len(per_perekam) >= MIN_PEREKAM,
        "tanpa_tumpang_tindih_manifest": not (set(daftar_id) & terpakai),
        "tanpa_lisensi_nd": all(not lisensi_itu_nd(k["lisensi"]) for k in terpilih),
    }
    semua_ok = all(syarat.values())

    hasil = {
        "catatan": "PROKSI C21. Hanya untuk dilaporkan, DILARANG dipakai memilih "
                   "ambang, fitur, atau hiperparameter.",
        "query": "cnt:indonesia grp:birds len:60-9999",
        "n_terpilih": len(terpilih),
        "total_menit": round(menit, 1),
        "bioregion": region_terpakai,
        "n_bioregion": len(region_terpakai),
        "n_rekaman_bioregion_tak_diketahui": n_region_tak_diketahui,
        "n_perekam": len(per_perekam),
        "per_perekam": dict(per_perekam),
        "sha256_daftar_id": sha,
        "daftar_id": daftar_id,
        "syarat": syarat,
        "syarat_semua_lulus": semua_ok,
        "rekaman": terpilih,
    }
    (OUT_DIR / "terpilih.json").write_text(
        json.dumps(hasil, indent=2, ensure_ascii=False))

    baris = [
        "# Panen proksi Xeno-canto Indonesia (S7, untuk C21)",
        "",
        "PROKSI. Diverifikasi terhadap label perekam Xeno-canto, BELUM oleh pakar.",
        "Set ini hanya dilaporkan; dilarang dipakai memilih apa pun.",
        "",
        "- Query: `cnt:indonesia grp:birds len:60-9999`",
        f"- Rekaman terkumpul dari API: {len(mentah)}",
        f"- Kandidat lolos saring: {len(kandidat)}",
        f"- Terpilih: {len(terpilih)} rekaman, {menit:.1f} menit",
        f"- Bioregion teridentifikasi: {len(region_terpakai)} ({', '.join(region_terpakai)})",
        f"- Rekaman tanpa bioregion jelas: {n_region_tak_diketahui} "
        "(tidak dihitung sebagai bioregion)",
        f"- Perekam berbeda: {len(per_perekam)}",
        f"- sha256 daftar id: `{sha}`",
        "",
        "## Alasan pembuangan",
        "",
        "| Alasan | Jumlah |",
        "|---|---:|",
    ]
    for k, n in buang.most_common():
        baris.append(f"| {k} | {n} |")
    baris += ["", "## Syarat B8-proksi", "", "| Syarat | Hasil |", "|---|---|"]
    for k, v in syarat.items():
        baris.append(f"| {k} | {'LULUS' if v else 'GAGAL'} |")
    baris += ["", "## Sebaran bioregion terpilih", "",
              "| Bioregion | Rekaman | Menit |", "|---|---:|---:|"]
    hit = collections.Counter(k["bioregion"] for k in terpilih)
    detik_region = collections.Counter()
    for k in terpilih:
        detik_region[k["bioregion"]] += k["durasi_s"]
    for region in sorted(hit):
        baris.append(f"| {region} | {hit[region]} | {detik_region[region]/60:.1f} |")

    (REPORTS / "proksi_xc_panen.md").write_text("\n".join(baris) + "\n")

    print(f"\nTerpilih {len(terpilih)} rekaman, {menit:.1f} menit")
    print(f"Bioregion teridentifikasi {len(region_terpakai)}: {', '.join(region_terpakai)}")
    print(f"Rekaman tanpa bioregion jelas: {n_region_tak_diketahui}")
    print(f"Perekam berbeda: {len(per_perekam)}")
    print(f"sha256 daftar id: {sha}")
    print("\nSyarat:")
    for k, v in syarat.items():
        print(f"  {'LULUS' if v else 'GAGAL'}  {k}")
    print(f"\nKeluaran: {OUT_DIR/'terpilih.json'}")
    print(f"Laporan: {REPORTS/'proksi_xc_panen.md'}")
    return 0 if semua_ok else 2


if __name__ == "__main__":
    sys.exit(main())
