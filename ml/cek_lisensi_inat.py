"""Cek lisensi iNaturalist lewat API untuk klip yang belum punya lisensi asli.

3.205 klip dari iNat Sounds punya lisensi "lihat-berkas-asli" -- lisensi
sebenarnya ada di API iNaturalist, bukan di dataset HF. Skrip ini mengambil
lisensi tiap observasi dari https://api.inaturalist.org/v1/observations/{id}.

Cache: ml/data/cache_api/ (1 file JSON per UUID, 1 req/detik).
Output: ml/data/manifest_lisensi_inat.json + ml/data/manifest_lisensi_inat.csv

Jalankan: source .venv/bin/activate && python ml/cek_lisensi_inat.py
"""
from __future__ import annotations

import csv
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML_DIR = ROOT / "ml"
MANIFEST_IN = ML_DIR / "data" / "manifest_latih_produksi.csv"
CACHE_DIR = ML_DIR / "data" / "cache_api"
OUT_JSON = ML_DIR / "data" / "manifest_lisensi_inat.json"
OUT_CSV = ML_DIR / "data" / "manifest_lisensi_inat.csv"

# Delay antar request (detik). iNat minta 1 req/detik.
DELAY_S = 1.1

# Lisensi yang dianggap TERLARANG (tidak boleh dipakai untuk karya turunan/model)
LISENSI_TERLARANG = {
    "cc-by-nc-nd", "cc-by-nd", "cc0",  # ND = no derivatives
    "all-rights-reserved", "",
}
# Lisensi yang MENGIZINKAN karya turunan
LISENSI_AMAN = {
    "cc-by", "cc-by-nc", "cc-by-sa", "cc-by-nc-sa",
    "cc-by-4.0", "cc-by-nc-4.0", "cc-by-sa-4.0", "cc-by-nc-sa-4.0",
}


def ambil_dari_api(uuid: str) -> dict | None:
    """Ambil lisensi observasi iNat dari API. Return dict atau None kalau gagal."""
    import urllib.error
    import urllib.request

    url = f"https://api.inaturalist.org/v1/observations/{uuid}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GemaHutan/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "uuid": uuid}
    except Exception as e:
        return {"error": str(e)[:200], "uuid": uuid}

    results = data.get("results", [])
    if not results:
        return {"error": "no results", "uuid": uuid}

    obs = results[0]
    return {
        "uuid": uuid,
        "inat_id": obs.get("id"),
        "license_code": obs.get("license_code", ""),
        "quality_grade": obs.get("quality_grade", ""),
        "species_guess": obs.get("species_guess", ""),
        "observed_on": obs.get("observed_on", ""),
        "user_login": obs.get("user", {}).get("login", ""),
    }


def lisensi_dilarang(license_code: str) -> bool:
    """Apakah lisensi termasuk terlarang (ND atau tidak ada)?"""
    if not license_code or not license_code.strip():
        return True
    lc = license_code.strip().lower()
    if lc in LISENSI_TERLARANG:
        return True
    # Deteksi varian ND: cc-by-nc-nd-4.0, CC BY-NC-ND 4.0, dll
    if "nd" in lc.replace("-", " ").split():
        return True
    return False


MANIFEST_V2 = None  # diisi di main(), perlu ROOT dulu


def muat_uuid_asli() -> dict[str, str]:
    """Peta clip_id -> UUID iNaturalist ASLI, diekstrak dari kolom local_path.

    clip_id (mis. inat-00018d64957143c2) BUKAN UUID iNat asli -- itu hash lain
    yang dipakai sebagai ID internal manifest. UUID asli (format
    8-4-4-4-12 hex berdash, dipakai iNaturalist) ada di nama file pada kolom
    local_path, contoh: audio_inat/negatives/Aves/Spesies__<uuid>.wav
    """
    import re
    pola_uuid = re.compile(
        r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
        re.IGNORECASE,
    )
    peta = {}
    v2_path = MANIFEST_V2 if MANIFEST_V2 else (MANIFEST_IN.parent / "manifest_v2.csv")
    if not v2_path.exists():
        return peta
    with open(v2_path, newline="") as f:
        for r in csv.DictReader(f):
            cid = r.get("clip_id", "")
            local_path = r.get("local_path", "")
            m = pola_uuid.search(local_path)
            if m:
                peta[cid] = m.group(1)
    return peta


def main() -> int:
    if not MANIFEST_IN.exists():
        print(f"ERROR: {MANIFEST_IN} tidak ditemukan. Jalankan ml/buat_manifest_lisensi.py dulu.")
        return 1

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    uuid_asli = muat_uuid_asli()
    print(f"UUID asli ditemukan dari manifest_v2.csv (via local_path): {len(uuid_asli)}")

    # Baca manifest, cari klip yang perlu dicek
    perlu_dicek = []
    sudah_aman = 0
    tanpa_uuid = 0
    with open(MANIFEST_IN, newline='') as f:
        for r in csv.DictReader(f):
            lic = (r.get("license") or "").strip().lower()
            sumber = (r.get("source") or "").strip()
            if lic == "lihat-berkas-asli" or (
                "inatsounds" in sumber and lic in ("", "unknown", "tidak diketahui")
            ):
                if r["clip_id"] in uuid_asli:
                    perlu_dicek.append(r["clip_id"])
                else:
                    tanpa_uuid += 1
            elif not lisensi_dilarang(r.get("license", "")):
                sudah_aman += 1

    if tanpa_uuid:
        print(f"PERINGATAN: {tanpa_uuid} klip iNat tidak punya UUID asli di local_path, "
              f"tidak bisa dicek ke API, dianggap TIDAK AMAN (dibuang dari training)")

    print(f"Total klip di manifest: {sudah_aman + len(perlu_dicek)}")
    print(f"Sudah aman (non-iNat / lisensi jelas): {sudah_aman}")
    print(f"Perlu dicek ke API iNat: {len(perlu_dicek)}")

    if not perlu_dicek:
        print("Tidak ada yang perlu dicek.")
        return 0

    # Proses satu per satu dengan cache
    hasil = {}
    dari_cache = 0
    dari_api = 0
    gagal = 0
    t0 = time.time()

    for i, clip_id in enumerate(perlu_dicek):
        uuid = uuid_asli[clip_id]  # UUID asli dari local_path, BUKAN clip_id
        cache_file = CACHE_DIR / f"{uuid}.json"

        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            dari_cache += 1
        else:
            data = ambil_dari_api(uuid)
            if data:
                cache_file.write_text(json.dumps(data, ensure_ascii=False))
            dari_api += 1
            time.sleep(DELAY_S)

        if data is None or "error" in data:
            gagal += 1
        hasil[clip_id] = data

        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            sisa = len(perlu_dicek) - (i + 1)
            eta = (elapsed / (i + 1)) * sisa if (i + 1) > 0 else 0
            print(f"  [{i+1}/{len(perlu_dicek)}] cache={dari_cache} api={dari_api} "
                  f"gagal={gagal} elapsed={elapsed/60:.1f}m ETA={eta/60:.1f}m")

    total_elapsed = time.time() - t0

    # Klasifikasi hasil
    dilarang = 0
    aman = 0
    tanpa_lisensi = 0
    rows = []

    for clip_id, data in hasil.items():
        if data is None or "error" in data:
            tanpa_lisensi += 1
            status = "gagal_api"
            lic = ""
        else:
            lic = data.get("license_code", "")
            if lisensi_dilarang(lic):
                dilarang += 1
                status = "dilarang"
            else:
                aman += 1
                status = "aman"

        rows.append({
            "clip_id": clip_id,
            "inat_uuid": clip_id.replace("inat-", ""),
            "license_code": lic,
            "status": status,
            "quality_grade": (data or {}).get("quality_grade", ""),
            "species_guess": (data or {}).get("species_guess", ""),
            "error": (data or {}).get("error", ""),
        })

    # Tulis output
    ringkasan = {
        "dijalankan": datetime.now(UTC).isoformat(),
        "total_dicek": len(perlu_dicek),
        "dari_cache": dari_cache,
        "dari_api": dari_api,
        "gagal_api": gagal,
        "lisensi_aman": aman,
        "lisensi_dilarang": dilarang,
        "tanpa_lisensi": tanpa_lisensi,
        "total_elapsed_s": round(total_elapsed, 1),
    }

    OUT_JSON.write_text(json.dumps({
        **ringkasan,
        "per_klip": rows,
    }, indent=2, ensure_ascii=False))

    with open(OUT_CSV, "w", newline='') as f:
        w = csv.DictWriter(f, fieldnames=[
            "clip_id", "inat_uuid", "license_code", "status",
            "quality_grade", "species_guess", "error",
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"\n{'='*60}")
    print(f"SELESAI dalam {total_elapsed/60:.1f} menit")
    print(f"  Dicek: {len(perlu_dicek)}")
    print(f"  Dari cache: {dari_cache}")
    print(f"  Dari API: {dari_api}")
    print(f"  Gagal API: {gagal}")
    print(f"  Lisensi AMAN: {aman}")
    print(f"  Lisensi DILARANG (ND/etc): {dilarang}")
    print(f"  Tanpa lisensi: {tanpa_lisensi}")
    print(f"Output: {OUT_JSON}")
    print(f"Output: {OUT_CSV}")

    # Rekomendasi
    if dilarang + tanpa_lisensi == 0:
        print("\nREKOMENDASI: Semua klip aman. Tidak ada yang perlu dikeluarkan.")
    else:
        print(f"\nREKOMENDASI: {dilarang + tanpa_lisensi} klip harus dikeluarkan "
              f"dari dataset latih ({dilarang} ND, {tanpa_lisensi} tanpa lisensi).")
        print(f"  Dataset latih akan menyusut dari {sudah_aman + len(perlu_dicek)} "
              f"menjadi {sudah_aman + aman} klip.")

    return 0


if __name__ == "__main__":
    sys.exit(main())