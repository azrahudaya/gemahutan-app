"""Unduh klip Xeno-canto untuk contoh negatif (non-target).

Menggantikan 3.202 klip iNat yang lisensinya tidak bisa diverifikasi.
Aturan:
- Spesies burung Indonesia + negara sekitar, BUKAN 25 spesies target
- DILARANG: semua spesies di pembagian_openset.json + field/other
- DILARANG: perekam yang ada di data evaluasi manapun
- DILARANG: ID XC yang sudah ada di korpus
- Lisensi tanpa ND, kualitas A/B/C
- Maks 8 klip/spesies, 3 klip/perekam/spesies
- Target 300+ spesies, maks 3000 klip
- 1 req/detik, cache di ml/data/cache_api/

Jalankan: source .venv/bin/activate && python ml/unduh_negatif_xc.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"
DATA_DIR = ML_DIR / "data"
CACHE_DIR = DATA_DIR / "cache_api"
AUDIO_DIR = DATA_DIR / "negatif_xc"
MANIFEST_OUT = DATA_DIR / "manifest_negatif_xc.csv"

XC_API = "https://xeno-canto.org/api/3/recordings"
XC_API_KEY = os.environ.get("XC_API_KEY", "").strip()
DELAY = 1.1  # 1 request/detik

# 25 spesies target (DILARANG diunduh)
TARGET_SPESIES = {
    "Aegithina tiphia", "Amaurornis phoenicurus", "Anthreptes malacensis",
    "Aplonis panayensis", "Arachnothera longirostra", "Centropus bengalensis",
    "Chalcophaps indica", "Cinnyris jugularis", "Cisticola juncidis",
    "Collared Kingfisher", "Copsychus saularis", "Dicrurus macrocercus",
    "Gallirallus striatus", "Gallus gallus", "Geopelia striata",
    "Halcyon smyrnensis", "Hirundo tahitica", "Lalage nigra",
    "Lonchura punctulata", "Orthotomus sutorius", "Passer montanus",
    "Pycnonotus aurigaster", "Pycnonotus goiavier", "Rhipidura javanica",
    "Spilopelia chinensis",
}


def muat_banned_species() -> set[str]:
    """Spesies yang DILARANG: pembagian_openset + field/other + target."""
    banned = set(TARGET_SPESIES)

    # pembagian_openset.json
    pembagian = DATA_DIR / "pembagian_openset.json"
    if pembagian.exists():
        p = json.loads(pembagian.read_text())
        for sp in p.get("spesies_pengecoh_pilih", []):
            banned.add(sp.replace("_", " "))
        for sp in p.get("spesies_pengecoh_lapor", []):
            banned.add(sp.replace("_", " "))

    # field/other manifest
    field_man = DATA_DIR / "field" / "manifest.csv"
    if field_man.exists():
        with open(field_man, newline="") as f:
            for row in csv.DictReader(f):
                if "other" in row.get("local_path", ""):
                    banned.add(row["species_scientific"].replace("_", " "))

    return banned


def muat_banned_recorders() -> set[str]:
    """Perekam yang DILARANG: semua yang ada di data evaluasi."""
    recorders = set()
    for man_path in [
        DATA_DIR / "field" / "manifest.csv",
        DATA_DIR / "uji_independen" / "manifest.csv",
        DATA_DIR / "manifest_v2.csv",
    ]:
        if not man_path.exists():
            continue
        with open(man_path, newline="") as f:
            for row in csv.DictReader(f):
                author = row.get("author", "").strip()
                if author:
                    recorders.add(author.lower())
    # Juga cek meta XC (struktur: {"recordings": {id: {...}}, "groups": {...}})
    meta = DATA_DIR / "xc_meta.json"
    if meta.exists():
        m = json.loads(meta.read_text())
        recs = m.get("recordings", m) if isinstance(m, dict) else {}
        if isinstance(recs, dict):
            for data in recs.values():
                if isinstance(data, dict):
                    rec = (data.get("rec") or "").strip().lower()
                    if rec:
                        recorders.add(rec)
        # groups: {perekam: [xc-id, ...]}
        groups = m.get("groups", {}) if isinstance(m, dict) else {}
        if isinstance(groups, dict):
            for author in groups:
                recorders.add(str(author).strip().lower())
    return recorders


def muat_banned_xc_ids() -> set[int]:
    """ID XC yang sudah ada di korpus mana pun."""
    ids = set()
    for man_path in [
        DATA_DIR / "manifest_v2.csv",
        DATA_DIR / "field" / "manifest.csv",
        DATA_DIR / "uji_independen" / "manifest.csv",
    ]:
        if not man_path.exists():
            continue
        with open(man_path, newline="") as f:
            for row in csv.DictReader(f):
                cid = row.get("clip_id", "").strip()
                if cid.startswith("xc-"):
                    try:
                        ids.add(int(cid[3:]))
                    except ValueError:
                        pass

    # Tambah dari xc_meta.json (recordings + xc_ids)
    meta = DATA_DIR / "xc_meta.json"
    if meta.exists():
        m = json.loads(meta.read_text())
        if isinstance(m, dict):
            recs = m.get("recordings", {})
            if isinstance(recs, dict):
                for cid in recs:
                    if cid.startswith("xc-"):
                        try:
                            ids.add(int(cid[3:]))
                        except ValueError:
                            pass
            for cid in m.get("xc_ids", []):
                if isinstance(cid, str) and cid.startswith("xc-"):
                    try:
                        ids.add(int(cid[3:]))
                    except ValueError:
                        pass
    return ids


def xc_search(spesies: str, page: int = 1) -> dict | None:
    """Cari rekaman XC v3 untuk spesies dengan kualitas A/B/C, lisensi non-ND."""
    import urllib.parse
    cache_key = f"xc3b_search_{spesies.replace(' ', '_')}_p{page}.json"
    cache_file = CACHE_DIR / cache_key
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    # XC v3: pakai tag sp: untuk spesies, key= untuk auth.
    # Kualitas tidak dibatasi di query (filter A/B/C dilakukan di kode)
    # supaya spesies langka tetap dapat hasil lebih banyak.
    query = f'sp:"{spesies}" len:3-120 grp:birds type:song,call'
    qs = urllib.parse.urlencode({"query": query, "key": XC_API_KEY, "page": str(page)})
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


def lisensi_aman(lic: str) -> bool:
    """Lisensi non-ND yang mengizinkan turunan (CC BY / BY-SA / BY-NC / BY-NC-SA)."""
    if not lic:
        return False
    low = lic.lower().strip().rstrip("/")
    if "sampling+" in low:
        return False
    # Ambil token versi kode lisensi, mis. "by-nc-nd" dari
    # "https://creativecommons.org/licenses/by-nc-nd/4.0/".
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


def download_xc(xc_id: int, out_path: Path, max_attempts: int = 3) -> bool:
    """Unduh satu klip XC sebagai MP3 mentah (soundfile membaca mp3 langsung).

    XC membatasi laju unduhan: respons berlebih berupa HTML, bukan audio.
    Periksa Content-Type; retry dengan jeda bertambah kalau bukan audio.
    """
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
            # Respons HTML/teks = rekaman tidak tersedia untuk unduhan publik.
            # Tidak ada gunanya retry; langsung menyerah.
            return False
        except Exception:
            # Galat jaringan/timeout: layak retry.
            pass
        if out_path.exists():
            out_path.unlink(missing_ok=True)
        time.sleep(1.5 * (attempt + 1))
    return False


def main() -> int:
    print("=== Unduh Negatif Xeno-canto ===")
    print(f"Disk: {os.popen('df -h . | tail -1').read().strip()}")

    banned_sp = muat_banned_species()
    banned_rec = muat_banned_recorders()
    banned_ids = muat_banned_xc_ids()

    print(f"Spesies target: {len(TARGET_SPESIES)}")
    print(f"Spesies dilarang total: {len(banned_sp)}")
    print(f"Perekam dilarang: {len(banned_rec)}")
    print(f"ID XC terpakai: {len(banned_ids)}")

    # Fase 1: kumpulkan daftar spesies kandidat dari XC Indonesia (broad)
    print("\n--- Fase 1: kumpulkan spesies kandidat ---")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    kandidat_names = {}  # scientific_name -> common_name
    negara_list = ["indonesia", "malaysia", "singapore", "brunei",
                   "philippines", "thailand"]
    import urllib.parse
    for negara in negara_list:
        if len(kandidat_names) >= 450:
            break
        for page in range(1, 41):
            cache_key = f"xc3_{negara}_broad_p{page}.json"
            cache_file = CACHE_DIR / cache_key

            if cache_file.exists():
                data = json.loads(cache_file.read_text())
            else:
                query = f'cnt:{negara} len:3-120 grp:birds type:song,call'
                qs = urllib.parse.urlencode({"query": query, "key": XC_API_KEY, "page": str(page)})
                url = f"{XC_API}?{qs}"
                try:
                    req = Request(url)
                    with urlopen(req, timeout=60) as resp:
                        data = json.loads(resp.read().decode())
                    cache_file.write_text(json.dumps(data, ensure_ascii=False))
                except Exception as e:
                    print(f"  {negara} hal {page} gagal: {e}")
                    continue
                time.sleep(DELAY)

            recordings = data.get("recordings", [])
            if not recordings:
                break

            for rec in recordings:
                en = rec.get("en", "").strip()
                sci = f"{rec.get('gen', '')} {rec.get('sp', '')}".strip()
                if not sci or not en:
                    continue
                if en in banned_sp or sci in banned_sp:
                    continue
                if rec.get("q", "") not in ("A", "B", "C"):
                    continue
                if not lisensi_aman(rec.get("lic", "")):
                    continue
                kandidat_names[sci] = en

            print(f"  {negara} hal {page}: {len(recordings)} rekaman, "
                  f"kandidat {len(kandidat_names)}")
            if len(kandidat_names) >= 450:
                break
            time.sleep(DELAY)

    print(f"\nSpesies kandidat: {len(kandidat_names)}")

    # Fase 2: per spesies, cari rekaman lalu unduh maks 8 klip (maks 3/perekam)
    print("\n--- Fase 2: unduh per spesies ---")
    n_spesies = 0
    n_klip = 0
    manifest = []
    ukuran_total = 0

    for sci, en in sorted(kandidat_names.items()):
        if n_spesies >= 320 or n_klip >= 3000:
            break

        # Cek disk tiap 20 spesies
        if n_spesies % 20 == 0 and n_spesies > 0:
            free = int(os.popen("df --output=avail . | tail -1").read().strip()) * 1024
            if free < 6 * 1024**3:
                print(f"\nDISK < 6 GB ({free/1024**3:.1f} GB). Berhenti.")
                break

        # Cari rekaman untuk spesies ini
        data = xc_search(sci, page=1)
        time.sleep(DELAY)
        if not data:
            continue
        recs = data.get("recordings", [])
        if not recs:
            continue

        # Filter perekam + lisensi + kualitas + id
        perekam_count = {}
        terpilih = []
        for rec in recs:
            author = (rec.get("rec") or "").strip().lower()
            if author in banned_rec:
                continue
            xc_id = int(rec["id"])
            if xc_id in banned_ids:
                continue
            if rec.get("q", "") not in ("A", "B", "C"):
                continue
            if not lisensi_aman(rec.get("lic", "")):
                continue
            cnt = perekam_count.get(author, 0)
            if cnt >= 3:
                continue
            perekam_count[author] = cnt + 1
            terpilih.append(rec)
            if len(terpilih) >= 8:
                break

        if len(terpilih) < 3:
            continue

        sp_dir = AUDIO_DIR / sci.replace(" ", "_")
        sp_dir.mkdir(parents=True, exist_ok=True)
        sukses = 0
        for rec in terpilih:
            xc_id = int(rec["id"])
            out_path = sp_dir / f"xc-{xc_id}.mp3"
            if download_xc(xc_id, out_path):
                ukuran_total += out_path.stat().st_size
                sukses += 1
                manifest.append({
                    "clip_id": f"xc-{xc_id}",
                    "source": "xeno-canto",
                    "source_url": f"https://xeno-canto.org/{xc_id}",
                    "species_scientific": sci.replace(" ", "_"),
                    "species_common": en,
                    "quality": rec.get("q", ""),
                    "license": rec.get("lic", ""),
                    "author": rec.get("rec", ""),
                    "country": rec.get("cnt", ""),
                    "recorded_on": rec.get("date", ""),
                    "lat": rec.get("lat", ""),
                    "lon": rec.get("lon", ""),
                    "duration_s": rec.get("length", ""),
                    "local_path": f"negatif_xc/{sci.replace(' ', '_')}/xc-{xc_id}.mp3",
                })
            time.sleep(0.8)

        # Simpan manifest incremental tiap 10 spesies
        if sukses >= 3:
            n_spesies += 1
            n_klip += sukses
            print(f"  [{n_spesies}] {en} ({sci}): {sukses} klip "
                  f"(total {n_klip} klip)")
            if n_spesies % 10 == 0:
                with open(MANIFEST_OUT, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=[
                        "clip_id", "source", "source_url", "species_scientific",
                        "species_common", "quality", "license", "author", "country",
                        "recorded_on", "lat", "lon", "duration_s", "local_path",
                    ])
                    w.writeheader()
                    for m in manifest:
                        w.writerow(m)

    # Tulis manifest
    print("\n=== SELESAI ===")
    print(f"Spesies: {n_spesies}, Klip: {n_klip}")

    with open(MANIFEST_OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "clip_id", "source", "source_url", "species_scientific",
            "species_common", "quality", "license", "author", "country",
            "recorded_on", "lat", "lon", "duration_s", "local_path",
        ])
        w.writeheader()
        for m in manifest:
            w.writerow(m)

    print(f"Manifest: {MANIFEST_OUT}")
    print(f"Ukuran audio: {ukuran_total/1e9:.2f} GB")

    return 0 if n_spesies >= 300 else 1


if __name__ == "__main__":
    sys.exit(main())