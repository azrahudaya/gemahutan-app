"""Panen korpus audio kondisi lapangan untuk evaluasi jujur.

Tiga kelompok yang diambil:
  1. xc_noisy  : rekaman Xeno-canto bertingkat kualitas C, D, E untuk 25 spesies
                 yang dikenal classifier. Ini audio kotor nyata, lisensi sama
                 dengan dataset utama.
  2. inat      : rekaman ponsel dari iNaturalist (berlisensi, kualitas riset) di
                 wilayah Indonesia, termasuk yang berisik seperti kondisi lapangan.
                 Lisensi ND dilewati karena pipeline ini membuat potongan klip.
  3. other     : rekaman kotor spesies Indonesia yang TIDAK dikenal classifier,
                 dipakai mengukur deteksi palsu.

Semua hasil ditulis ke ml/data/field/ beserta manifest berisi provenance lengkap
(sumber, penulis, lisensi, tanggal, negara, koordinat).

Pakai:
    cd ml && ../.venv/bin/python data/field_corpus.py --per-species 6 --per-other 4
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_DIR))

import download  # noqa: E402  (XC_API_KEY di modul ini dibaca saat import)
from download import download_file, fetch_xc, sha256_file  # noqa: E402

ML_DIR = DATA_DIR.parent
REPO_DIR = ML_DIR.parent


def _muat_env() -> None:
    """Ambil XC_API_KEY dari .env repo kalau belum ada di environment.

    Penting: download.py membaca kuncinya sekali saat import, jadi variabel di
    modul itu harus ikut diperbarui, bukan hanya os.environ.
    """
    global XC_API_KEY
    if XC_API_KEY:
        download.XC_API_KEY = XC_API_KEY
        return
    berkas = REPO_DIR / ".env"
    if not berkas.exists():
        return
    for baris in berkas.read_text().splitlines():
        if baris.startswith("XC_API_KEY="):
            XC_API_KEY = baris.split("=", 1)[1].strip()
            os.environ["XC_API_KEY"] = XC_API_KEY
            download.XC_API_KEY = XC_API_KEY
FIELD_DIR = DATA_DIR / "field"
AUDIO_DIR = FIELD_DIR / "audio"
MANIFEST = FIELD_DIR / "manifest.csv"
CACHE = FIELD_DIR / "cache.json"
LABEL_MAP = ML_DIR / "embeddings" / "label_map.json"

XC_API_KEY = os.getenv("XC_API_KEY", "")
UA = {"User-Agent": "GemaHutan/0.1 (riset akademik)"}
LISENSI_DILARANG = ("-nd", "/nd", "nd/", "noderiv",
                    "no-deriv")  # ND: pipeline memotong klip jadi karya turunan

# Spesies Indonesia yang tidak ada di label map, dipakai sebagai pengecoh.
SPESIES_PENGECOH = [
    "Acridotheres javanicus",
    "Collocalia linchi",
    "Alcedo meninting",
    "Aethopyga mystacalis",
    "Centropus sinensis",
    "Corvus enca",
    "Orthotomus ruficeps",
    "Dicaeum trochileum",
    "Nectarinia jugularis",
    "Turnix suscitator",
]


def baca_label_map() -> list[str]:
    data = json.loads(LABEL_MAP.read_text())
    return sorted(k for k in data if not k.startswith("_"))


def ambil_json(url: str, timeout: int = 40):
    req = urllib.request.Request(url, headers=UA)
    for percobaan in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except Exception as exc:
            if percobaan == 2:
                print(f"    gagal ambil {url[:90]}: {str(exc)[:70]}")
                return None
            time.sleep(3)
    return None


def query_xc(query: str, cache: dict):
    """Query Xeno-canto dengan cache supaya tidak mengulang permintaan."""
    if query in cache:
        return cache[query]
    hasil = fetch_xc(query, page=1, per_page=50) or {}
    cache[query] = hasil
    CACHE.write_text(json.dumps(cache))
    time.sleep(1.5)  # sopan ke API
    return hasil


def lisensi_ditolak(lic: str | None) -> bool:
    """True kalau lisensi tidak boleh dipakai. ND ditolak: klip dipotong.

    Pencocokan pakai penanda utuh ("-nd", "/nd", "nd/"), bukan substring "nd",
    supaya "cc-by-nc" tidak ikut tertolak.
    """
    if not lic:
        return True
    return any(tanda in lic.lower() for tanda in LISENSI_DILARANG)


def simpan_baris(sci: str, nama_group: str, sumber: str, meta: dict) -> dict:
    return {
        "clip_id": meta["clip_id"],
        "group": nama_group,
        "source": sumber,
        "source_url": meta.get("source_url", ""),
        "species_scientific": sci,
        "species_common": meta.get("common", ""),
        "quality": meta.get("quality", ""),
        "license": meta.get("license", ""),
        "author": meta.get("author", ""),
        "country": meta.get("country", ""),
        "recorded_on": meta.get("recorded_on", ""),
        "lat": meta.get("lat", ""),
        "lon": meta.get("lon", ""),
        "duration_s": meta.get("duration_s", ""),
        "local_path": meta["local_path"],
        "sha256": meta.get("sha256", ""),
    }


def panen_xc_spesies(spesies: list[str], per_spesies: int, group: str, cache: dict,
                     skip_ids: set, baris: list) -> int:
    """Ambil rekaman C/D/E untuk tiap spesies, Indonesia dulu lalu global."""
    jumlah = 0
    for sci in spesies:
        folder = AUDIO_DIR / group / sci.replace(" ", "_")
        folder.mkdir(parents=True, exist_ok=True)
        terkumpul = 0
        for cakupan in ("cnt:Indonesia", ""):
            if terkumpul >= per_spesies:
                break
            query = f'sp:"{sci}" q_lt:B {cakupan}'.strip()
            hasil = query_xc(query, cache) or {}
            for rec in hasil.get("recordings", []):
                if terkumpul >= per_spesies:
                    break
                rid = str(rec.get("id"))
                if rid in skip_ids:
                    continue
                if lisensi_ditolak(rec.get("lic")):
                    # ND tidak dipakai: klip dipotong, dan potongan itu karya turunan.
                    continue
                berkas = rec.get("file") or ""
                if not berkas:
                    continue
                ext = ".mp3" if ".mp3" in berkas.lower() else Path(berkas).suffix or ".mp3"
                tujuan = folder / f"xc-{rid}{ext}"
                if not tujuan.exists() and not download_file(berkas, str(tujuan)):
                    continue
                skip_ids.add(rid)
                terkumpul += 1
                baris.append(simpan_baris(sci, group, "xeno-canto", {
                    "clip_id": f"xc-{rid}",
                    "source_url": rec.get("url", f"https://xeno-canto.org/{rid}"),
                    "common": rec.get("en", ""),
                    "quality": rec.get("q", ""),
                    "license": rec.get("lic", ""),
                    "author": rec.get("rec", ""),
                    "country": rec.get("cnt", ""),
                    "recorded_on": rec.get("date", ""),
                    "lat": rec.get("lat", ""),
                    "lon": rec.get("lon", ""),
                    "duration_s": rec.get("length", ""),
                    "local_path": str(tujuan.relative_to(DATA_DIR)),
                    "sha256": sha256_file(str(tujuan)),
                }))
        print(f"    {sci}: {terkumpul} rekaman kotor")
        jumlah += terkumpul
    return jumlah


def panen_inat(spesies: list[str], per_spesies: int, skip_ids: set, baris: list) -> int:
    """Ambil rekaman ponsel iNaturalist yang berlisensi jelas."""
    bbox = "swlat=-11&swlng=95&nelat=6&nelng=141"
    jumlah = 0
    for sci in spesies:
        taxa = ambil_json(
            "https://api.inaturalist.org/v1/taxa?q=" + urllib.parse.quote(sci)
            + "&rank=species&per_page=1"
        )
        hasil_taxa = (taxa or {}).get("results") or []
        if not hasil_taxa:
            print(f"    {sci}: takson tidak ditemukan di iNaturalist")
            continue
        taxon_id = hasil_taxa[0]["id"]
        obs = ambil_json(
            f"https://api.inaturalist.org/v1/observations?taxon_id={taxon_id}&{bbox}"
            "&sounds=true&licensed=true&quality_grade=research&per_page=30&order_by=votes"
        )
        folder = AUDIO_DIR / "inat" / sci.replace(" ", "_")
        folder.mkdir(parents=True, exist_ok=True)
        terkumpul = 0
        for o in (obs or {}).get("results", []):
            if terkumpul >= per_spesies:
                break
            for snd in o.get("sounds") or []:
                if terkumpul >= per_spesies:
                    break
                if lisensi_ditolak(snd.get("license_code")):
                    continue
                url_audio = snd.get("file_url")
                if not url_audio:
                    continue
                oid = str(o.get("id"))
                if f"inat-{oid}" in skip_ids:
                    continue
                ext = Path(urllib.parse.urlparse(url_audio).path).suffix or ".m4a"
                tujuan = folder / f"inat-{oid}{ext}"
                if not tujuan.exists() and not download_file(url_audio, str(tujuan)):
                    continue
                skip_ids.add(f"inat-{oid}")
                terkumpul += 1
                baris.append(simpan_baris(sci, "inat", "inaturalist", {
                    "clip_id": f"inat-{oid}",
                    "source_url": f"https://www.inaturalist.org/observations/{oid}",
                    "common": ((o.get("taxon") or {}).get("preferred_common_name") or ""),
                    "quality": snd.get("license_code", ""),
                    "license": snd.get("license_code", ""),
                    "author": (o.get("user") or {}).get("login", ""),
                    "country": o.get("place_guess", ""),
                    "recorded_on": o.get("observed_on", ""),
                    "lat": (o.get("geojson") or {}).get("coordinates", ["", ""])[1],
                    "lon": (o.get("geojson") or {}).get("coordinates", ["", ""])[0],
                    "duration_s": "",
                    "local_path": str(tujuan.relative_to(DATA_DIR)),
                    "sha256": sha256_file(str(tujuan)),
                }))
        print(f"    {sci}: {terkumpul} rekaman ponsel iNaturalist")
        jumlah += terkumpul
        time.sleep(1)
    return jumlah


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-species", type=int, default=6)
    parser.add_argument("--per-other", type=int, default=4)
    parser.add_argument("--sources", default="xc,inat")
    args = parser.parse_args()

    _muat_env()
    if not XC_API_KEY:
        print("XC_API_KEY belum ada di .env, panen Xeno-canto dilewati")

    FIELD_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    baris: list[dict] = []
    skip_ids: set[str] = set()
    sumber = [s.strip() for s in args.sources.split(",")]
    target = baca_label_map()
    print(f"spesies target classifier: {len(target)}")

    if "xc" in sumber and XC_API_KEY:
        print("Xeno-canto kualitas C/D/E untuk spesies target:")
        panen_xc_spesies(target, args.per_species, "xc_noisy", cache, skip_ids, baris)
    if "inat" in sumber:
        print("iNaturalist rekaman ponsel untuk spesies target:")
        panen_inat(target, args.per_species, skip_ids, baris)
    if "xc" in sumber and XC_API_KEY:
        print("Xeno-canto kualitas C/D/E untuk spesies pengecoh:")
        panen_xc_spesies(SPESIES_PENGECOH, args.per_other, "other", cache, skip_ids, baris)

    if baris:
        with MANIFEST.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(baris[0].keys()))
            writer.writeheader()
            writer.writerows(baris)

    per_group: dict[str, int] = {}
    for b in baris:
        per_group[b["group"]] = per_group.get(b["group"], 0) + 1
    print("\nringkasan korpus lapangan:")
    for k, v in sorted(per_group.items()):
        print(f"  {k}: {v} berkas")
    print(f"  manifest: {MANIFEST.relative_to(ML_DIR.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
