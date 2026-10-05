"""Unduh klip Xeno-canto untuk 8 spesies pemicu (S4, ML_09).

8 spesies pemicu teratas dari ml/reports/pemicu_palsu.md (urut jumlah pemicu):
Orthotomus_ruficeps, Accipiter_badius, Dicaeum_trochileum, Aethopyga_mystacalis,
Hemipus_hirundinaceus, Merops_viridis, Centropus_sinensis, Dendrocygna_arcuata.

PENTING: klip evaluasi di ml/data/field/audio/other/<spesies>/ dan ID yang
disebut di ml/data/pembagian_openset.json TIDAK diunduh ulang di sini — itu
data uji yang harus tetap murni untuk mengukur FP sesudah model dilatih.
Script ini hanya mengunduh klip XC TAMBAHAN (ID berbeda) untuk jadi data latih
kelas pemicu, supaya tidak ada kebocoran data latih->uji.

Aturan sama seperti unduh_negatif_xc.py:
- Lisensi tanpa ND, kualitas A/B/C
- Maks 20 klip/spesies (spesies ini lebih sedikit datanya dari negatif umum)
- 1 req/detik, cache di ml/data/cache_api/

Jalankan: source .venv/bin/activate && python ml/unduh_pemicu_xc.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"
DATA_DIR = ML_DIR / "data"
CACHE_DIR = DATA_DIR / "cache_api"
AUDIO_DIR = DATA_DIR / "pemicu_xc"
MANIFEST_OUT = DATA_DIR / "manifest_pemicu_xc.csv"
PEMBAGIAN_FILE = DATA_DIR / "pembagian_openset.json"

XC_API = "https://xeno-canto.org/api/3/recordings"
XC_API_KEY = os.environ.get("XC_API_KEY", "").strip()
DELAY = 1.1
MAKS_KLIP_PER_SPESIES = 20

# 8 spesies pemicu teratas, urut jumlah pemicu di pemicu_palsu.md
SPESIES_PEMICU_BAWAAN = [
    "Orthotomus ruficeps",
    "Accipiter badius",
    "Dicaeum trochileum",
    "Aethopyga mystacalis",
    "Hemipus hirundinaceus",
    "Merops viridis",
    "Centropus sinensis",
    "Dendrocygna arcuata",
]


def muat_xc_key() -> str:
    if XC_API_KEY:
        return XC_API_KEY
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("XC_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("XC_API_KEY tidak ditemukan di env atau .env")


def muat_id_terpakai() -> set[int]:
    """ID XC yang sudah dipakai di manifest manapun ATAU di set evaluasi (other).

    Dicegah dobel supaya data latih pemicu tidak overlap dengan klip uji di
    field/audio/other (dipakai untuk mengukur FP di pemicu_palsu.md).
    """
    ids: set[int] = set()
    for man_path in [
        DATA_DIR / "manifest_v2.csv",
        DATA_DIR / "manifest_negatif_xc.csv",
        DATA_DIR / "field" / "manifest.csv",
        DATA_DIR / "uji_independen" / "manifest.csv",
    ]:
        if not man_path.exists():
            continue
        with open(man_path, newline="") as f:
            for row in csv.DictReader(f):
                cid = (row.get("clip_id") or "").strip()
                if cid.startswith("xc-"):
                    try:
                        ids.add(int(cid[3:]))
                    except ValueError:
                        pass
    return ids


def muat_perekam_terpakai() -> set[str]:
    """Nama perekam yang sudah menyumbang klip ke pool EVALUASI.

    ML_10 K4 mewajibkan "id dan perekam yang ada di pool evaluasi dibuang".
    Membuang id saja tidak cukup: satu perekam biasanya mengunggah beberapa
    rekaman dari lokasi dan perangkat yang sama, jadi klip latih dari perekam
    yang juga ada di pool uji membuat model mengenali ciri rekamannya, bukan
    suara burungnya. Angka FP-nya lalu terlihat bagus tanpa alasan yang sah.

    Sumber: manifest korpus lapangan dan uji independen, yaitu berkas yang
    dipakai mengukur FP di pemicu_palsu.md dan pembagian_openset.json.
    """
    perekam: set[str] = set()
    for man_path in [
        DATA_DIR / "field" / "manifest.csv",
        DATA_DIR / "uji_independen" / "manifest.csv",
    ]:
        if not man_path.exists():
            continue
        with open(man_path, newline="") as f:
            for row in csv.DictReader(f):
                nama = (row.get("author") or "").strip()
                if nama:
                    perekam.add(nama.casefold())
    return perekam


def lisensi_aman(lic: str) -> bool:
    if not lic:
        return False
    low = lic.lower().strip().rstrip("/")
    if "sampling+" in low:
        return False
    bagian = [p for p in low.split("/") if p]
    if not bagian:
        return False
    tail = bagian[-1]
    if tail.replace(".", "").isdigit() and len(bagian) >= 2:
        tail = bagian[-2]
    tokens = tail.replace("-", " ").replace("_", " ").split()
    if "nd" in tokens or "nd" == tail.strip():
        return False
    return True


def xc_search(spesies: str, key: str, page: int = 1) -> dict | None:
    cache_key = f"xc3_pemicu_{spesies.replace(' ', '_')}_p{page}.json"
    cache_file = CACHE_DIR / cache_key
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    query = f'sp:"{spesies}" len:3-120 grp:birds type:song,call'
    qs = urllib.parse.urlencode({"query": query, "key": key, "page": str(page)})
    url = f"{XC_API}?{qs}"
    try:
        req = Request(url)
        with urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  API error for {spesies}: {e}")
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data, ensure_ascii=False))
    return data


def download_xc(xc_id: int, out_path: Path, max_attempts: int = 3) -> bool:
    if out_path.exists() and out_path.stat().st_size > 5000:
        return True
    url = f"https://xeno-canto.org/{xc_id}/download"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "audio/mpeg,audio/*;q=0.9,*/*;q=0.8",
    }
    for attempt in range(max_attempts):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=60) as resp:
                ctype = resp.headers.get("Content-Type", "")
                data = resp.read()
            if "audio" in ctype and len(data) > 5000:
                out_path.write_bytes(data)
                return True
            return False
        except Exception:
            pass
        if out_path.exists():
            out_path.unlink(missing_ok=True)
        time.sleep(1.5 * (attempt + 1))
    return False


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Unduh klip Xeno-canto non-ND per spesies (K4 pemicu, K5 spesies lemah)",
    )
    ap.add_argument("--spesies", nargs="+", default=None,
                    help="daftar nama ilmiah; bawaannya 8 spesies pemicu K4")
    ap.add_argument("--maks-klip", type=int, default=MAKS_KLIP_PER_SPESIES,
                    help="batas klip per spesies")
    ap.add_argument("--audio-dir", default=str(AUDIO_DIR),
                    help="folder tujuan audio")
    ap.add_argument("--manifest-out", default=str(MANIFEST_OUT),
                    help="lokasi manifest CSV")
    ap.add_argument("--maks-per-perekam", type=int, default=0,
                    help="batas klip per perekam, 0 = tanpa batas")
    args = ap.parse_args()

    spesies_list = args.spesies or SPESIES_PEMICU_BAWAAN
    maks_klip = args.maks_klip
    audio_dir = Path(args.audio_dir)
    manifest_out = Path(args.manifest_out)

    print("=== Unduh klip Xeno-canto non-ND ===")
    print(f"Spesies: {len(spesies_list)}, maks {maks_klip} klip per spesies")
    key = muat_xc_key()
    id_terpakai = muat_id_terpakai()
    perekam_evaluasi = muat_perekam_terpakai()
    print(f"ID XC sudah terpakai (dilarang dobel): {len(id_terpakai)}")
    print(f"Perekam di pool evaluasi (dilarang dipakai melatih): {len(perekam_evaluasi)}")

    audio_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    dibuang = {"id_dobel": 0, "perekam_evaluasi": 0, "lisensi_nd": 0,
               "kualitas": 0, "kuota_perekam": 0}

    for spesies in spesies_list:
        sp_dir_name = spesies.replace(" ", "_")
        sp_dir = audio_dir / sp_dir_name
        sp_dir.mkdir(parents=True, exist_ok=True)
        per_perekam: dict[str, int] = {}

        diambil = 0
        page = 1
        while diambil < maks_klip and page <= 5:
            data = xc_search(spesies, key, page)
            time.sleep(DELAY)
            if data is None:
                break
            recs = data.get("recordings", [])
            if not recs:
                break

            for rec in recs:
                if diambil >= maks_klip:
                    break
                try:
                    xc_id = int(rec.get("id"))
                except (TypeError, ValueError):
                    continue
                if xc_id in id_terpakai:
                    dibuang["id_dobel"] += 1
                    continue
                perekam = (rec.get("rec") or "").strip()
                # Perekam yang klipnya ada di pool evaluasi tidak boleh ikut
                # melatih: ciri perangkat dan lokasinya akan terbawa dan
                # angka FP jadi bagus tanpa alasan yang sah.
                if perekam and perekam.casefold() in perekam_evaluasi:
                    dibuang["perekam_evaluasi"] += 1
                    continue
                if args.maks_per_perekam and perekam:
                    if per_perekam.get(perekam.casefold(), 0) >= args.maks_per_perekam:
                        dibuang["kuota_perekam"] += 1
                        continue
                quality = (rec.get("q") or "").strip().upper()
                if quality not in ("A", "B", "C"):
                    dibuang["kualitas"] += 1
                    continue
                lic = rec.get("lic", "")
                if not lisensi_aman(lic):
                    dibuang["lisensi_nd"] += 1
                    continue

                out_path = sp_dir / f"xc-{xc_id}.mp3"
                ok = download_xc(xc_id, out_path)
                time.sleep(DELAY)
                if not ok:
                    continue

                id_terpakai.add(xc_id)
                if perekam:
                    kunci = perekam.casefold()
                    per_perekam[kunci] = per_perekam.get(kunci, 0) + 1
                diambil += 1
                rows.append({
                    "clip_id": f"xc-{xc_id}",
                    "source": "xeno-canto",
                    "source_url": f"https://xeno-canto.org/{xc_id}",
                    "species_scientific": sp_dir_name,
                    "species_common": rec.get("en", ""),
                    "quality": quality,
                    "license": lic,
                    "author": rec.get("rec", ""),
                    "country": rec.get("cnt", ""),
                    "recorded_on": rec.get("date", ""),
                    "lat": rec.get("lat", ""),
                    "lon": rec.get("lng", ""),
                    "duration_s": rec.get("length", ""),
                    # Relatif terhadap ml/data supaya manifest tetap benar
                    # walau --audio-dir diarahkan ke folder lain (mis. K5).
                    "local_path": f"{audio_dir.name}/{sp_dir_name}/xc-{xc_id}.mp3",
                })

            total_available = int(data.get("numRecordings", 0))
            if page * len(recs) >= total_available:
                break
            page += 1

        n_perekam = len(per_perekam)
        cukup = "" if n_perekam >= 5 else "  <- perekam < 5, batas data"
        print(f"  {spesies}: {diambil} klip dari {n_perekam} perekam{cukup}")

    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "clip_id", "source", "source_url", "species_scientific",
            "species_common", "quality", "license", "author", "country",
            "recorded_on", "lat", "lon", "duration_s", "local_path",
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"\nTotal klip: {len(rows)}")
    print("Dibuang saat menyaring:")
    for alasan, n in dibuang.items():
        print(f"  {alasan}: {n}")
    print(f"Manifest: {manifest_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
