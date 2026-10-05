"""Gabungkan korpus GemaHutan lama dengan tiga sumber eksternal menjadi satu manifest.

Sumber:
1. `ml/data/manifest.csv` -- 924 klip Xeno-canto yang sudah dipakai sekarang.
2. ULM-DS-Lab ND-free -- 1050 klip, hanya Cinnyris jugularis yang masuk target.
3. SEA-Bird ND-free -- 6 spesies target, sisanya jadi bahan `_negative`.
4. iNatSounds -- semuanya `_negative`.

Aturan penting:

- Dedup wajib lewat sha256 berkas, bukan cuma lewat ID. Tiga sumber eksternal ini
  sama-sama berasal dari Xeno-canto, jadi rekaman yang sama bisa muncul di dua
  sumber. Klip kembar yang menyeberang latih dan uji membuat akurasi uji palsu.
- Split lama DIPERTAHANKAN apa adanya. Tujuannya supaya angka uji baru bisa
  dibandingkan langsung dengan baseline 0,6772. Data baru hanya masuk train.
- Subset SEA-Bird 44 kHz dipakai, bukan 16 kHz, supaya mutu spektrogram lebih
  baik. Memakai keduanya berarti audio yang sama masuk dua kali dengan nama
  berbeda, dan itu bentuk kebocoran data.

Keluaran:
- `ml/data/manifest_v2.csv`
- `ml/data/splits_v2.json`
- cetakan ringkasan ke stdout
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
MANIFEST_LAMA = BASE / "manifest.csv"
OUT_MANIFEST = BASE / "manifest_v2.csv"
OUT_SPLITS = BASE / "splits_v2.json"

# Folder data eksternal.
DIR_ULM = BASE / "audio_ulm"
DIR_SEABIRD = BASE / "audio_seabird"
DIR_INAT = BASE / "audio_inat"

# 25 spesies yang dikenal classifier lokal.
TARGET = {
    "Aegithina tiphia", "Amaurornis phoenicurus", "Anthreptes malacensis",
    "Aplonis panayensis", "Arachnothera longirostra", "Centropus bengalensis",
    "Chalcophaps indica", "Cinnyris jugularis", "Cisticola juncidis",
    "Corvus macrorhynchos", "Dicrurus macrocercus", "Gallus gallus",
    "Geopelia striata", "Haliastur indus", "Hirundo tahitica",
    "Lonchura punctulata", "Merops philippinus", "Orthotomus sutorius",
    "Passer montanus", "Prinia familiaris", "Pycnonotus aurigaster",
    "Pycnonotus goiavier", "Rhipidura javanica", "Spilopelia chinensis",
    "Todiramphus chloris",
}

# Nama umum SEA-Bird ke nama ilmiah. Enam yang bertanda TARGET masuk kelasnya,
# sisanya jadi bahan _negative.
SEABIRD_MAP = {
    "Collared Kingfisher": ("Todiramphus chloris", True),
    "Common Iora": ("Aegithina tiphia", True),
    "Zebra Dove": ("Geopelia striata", True),
    "Common Tailorbird": ("Orthotomus sutorius", True),
    "Olive-backed Sunbird": ("Cinnyris jugularis", True),
    "Spotted Dove": ("Spilopelia chinensis", True),
    "Asian Koel": ("Eudynamys scolopaceus", False),
    "Common Myna": ("Acridotheres tristis", False),
    "Large-tailed Nightjar": ("Caprimulgus macrurus", False),
    "White-throated Kingfisher": ("Halcyon smyrnensis", False),
}

KOLOM = [
    "clip_id", "source", "source_url", "species_scientific", "species_common",
    "split", "duration_s", "sample_rate", "quality", "license", "sha256", "local_path",
]


def sha256_berkas(path: Path, batas_byte: int = 8 * 1024 * 1024) -> str:
    """Hash isi berkas. Untuk berkas besar hanya bagian awal dan akhir yang dibaca."""
    h = hashlib.sha256()
    ukuran = path.stat().st_size
    with open(path, "rb") as f:
        if ukuran <= batas_byte:
            h.update(f.read())
        else:
            h.update(f.read(batas_byte // 2))
            f.seek(-batas_byte // 2, 2)
            h.update(f.read())
    return h.hexdigest()


def xc_id(clip_id: str) -> str | None:
    """Ambil angka ID Xeno-canto dari clip_id, atau None kalau bukan dari XC.

    Bentuk clip_id yang harus dikenali:
      xc-1076362          -> 1076362   (manifest lama)
      ulm-1059986         -> 1059986   (ULM, berkas <id>.mp3)
      sb-xc121824_25891   -> 121824    (SEA-Bird, berkas xc<id>_<ms>.wav)

    Versi sebelumnya tidak mengenali bentuk ketiga karena mengambil bagian
    setelah tanda hubung apa adanya, sehingga `xc121824_25891` gagal jadi angka
    dan klip SEA-Bird lolos dari penyaringan ID. Akibatnya 14 ID rekaman muncul
    di train dan test sekaligus.
    """
    teks = clip_id
    # buang awalan sumber (ulm-, sb-, xc-)
    if "-" in teks:
        teks = teks.split("-", 1)[1]
    # buang awalan xc dan bagian segmen setelah garis bawah
    teks = teks.split("_")[0].lstrip("xcXC")
    return teks if teks.isdigit() else None


def xc_id_dari_path(local_path: str) -> str | None:
    """Sama seperti xc_id tetapi membaca nama berkas, lebih tahan bentuk aneh."""
    nama = local_path.split("/")[-1].split(".")[0]
    return xc_id(nama)


def baca_manifest_lama() -> list[dict]:
    if not MANIFEST_LAMA.exists():
        return []
    return list(csv.DictReader(open(MANIFEST_LAMA, encoding="utf-8")))


def baris_ulm() -> list[dict]:
    """Baris dari ULM ND-free. Hanya species target atau _negative."""
    out = []
    if not DIR_ULM.exists():
        return out
    for berkas in sorted(DIR_ULM.rglob("*.mp3")):
        ilmiah = berkas.parent.name.replace("_", " ")
        umum = ""
        target = ilmiah in TARGET
        out.append({
            "clip_id": f"ulm-{berkas.stem}",
            "source": "ulm-ds-lab",
            "source_url": f"https://xeno-canto.org/{berkas.stem}",
            "species_scientific": ilmiah if target else "_negative",
            "species_common": umum,
            "split": "train",
            "duration_s": "",
            "sample_rate": "48000",
            "quality": "",
            "license": "cc-by-nc-sa-4.0",
            "sha256": sha256_berkas(berkas),
            "local_path": str(berkas.relative_to(BASE)),
            "_target": target,
        })
    return out


def baris_seabird() -> list[dict]:
    """Baris dari SEA-Bird ND-free, subset 44 kHz saja."""
    out = []
    folder = DIR_SEABIRD / "seabird44k"
    if not folder.exists():
        return out
    for berkas in sorted(folder.rglob("*.wav")):
        umum = berkas.parent.name
        ilmiah, target = SEABIRD_MAP.get(umum, ("", False))
        if not ilmiah:
            continue
        out.append({
            "clip_id": f"sb-{berkas.stem}",
            "source": "sea-bird",
            "source_url": f"https://xeno-canto.org/{berkas.stem.split('_')[0].lstrip('xcXC')}",
            "species_scientific": ilmiah if target else "_negative",
            "species_common": umum,
            "split": "train",
            "duration_s": "0:03",
            "sample_rate": "44100",
            "quality": "",
            "license": "cc-by-nc-sa-4.0",
            "sha256": sha256_berkas(berkas),
            "local_path": str(berkas.relative_to(BASE)),
            "_target": target,
        })
    return out


def baris_inat() -> list[dict]:
    """Baris dari iNatSounds. Semuanya bahan _negative."""
    out = []
    if not DIR_INAT.exists():
        return out
    for berkas in sorted(DIR_INAT.rglob("*.wav")):
        kelas = berkas.parent.name
        out.append({
            "clip_id": f"inat-{hashlib.sha1(str(berkas).encode()).hexdigest()[:16]}",
            "source": f"inatsounds-{kelas.lower()}",
            "source_url": "https://huggingface.co/datasets/DBD-research-group/inat_sounds",
            "species_scientific": "_negative",
            "species_common": kelas,
            "split": "train",
            "duration_s": "",
            "sample_rate": "",
            "quality": "",
            "license": "lihat-berkas-asli",
            "sha256": sha256_berkas(berkas),
            "local_path": str(berkas.relative_to(BASE)),
            "_target": False,
        })
    return out


def main() -> None:
    lama = baca_manifest_lama()
    print("manifest lama       :", len(lama), "baris")

    id_lama = {r["clip_id"] for r in lama}
    id_xc_lama = {xc_id_dari_path(r["local_path"]) for r in lama} - {None}
    hash_lama = {r["sha256"] for r in lama}
    print("ID Xeno-canto di manifest lama :", len(id_xc_lama))

    baru = baris_ulm() + baris_seabird() + baris_inat()
    print("kandidat baru       :", len(baru))

    # Dedup 1: clip_id sudah ada.
    tahap1 = [r for r in baru if r["clip_id"] not in id_lama]
    buang_id = len(baru) - len(tahap1)

    # Dedup 2: ID Xeno-canto sudah dipakai manifest lama.
    tahap2 = []
    buang_xc = 0
    for r in tahap1:
        angka = xc_id_dari_path(r["local_path"])
        if angka and angka in id_xc_lama:
            buang_xc += 1
            continue
        tahap2.append(r)

    # Dedup 3: isi berkas sama (hash).
    terlihat = set(hash_lama)
    tahap3 = []
    buang_hash = 0
    for r in tahap2:
        if r["sha256"] in terlihat:
            buang_hash += 1
            continue
        terlihat.add(r["sha256"])
        tahap3.append(r)

    print(f"dibuang karena clip_id duplikat : {buang_id}")
    print(f"dibuang karena ID XC duplikat   : {buang_xc}")
    print(f"dibuang karena hash duplikat    : {buang_hash}")

    for r in lama + tahap3:
        r.pop("_target", None)

    # Dedup terakhir: buang baris berisi audio yang byte-nya identik.
    # Kebocoran lintas split sudah nol di tahap sebelumnya, jadi yang tersisa
    # hanya kembar di dalam train. Baris test dan val didahulukan supaya tidak
    # ada satu pun yang ikut terbuang.
    urut = [r for r in lama if r["split"] in ("test", "val")]
    urut += [r for r in lama if r["split"] not in ("test", "val")]
    urut += tahap3

    terlihat_akhir: set[str] = set()
    semua: list[dict] = []
    kembar_akhir = 0
    for r in urut:
        if r["sha256"] in terlihat_akhir:
            kembar_akhir += 1
            continue
        terlihat_akhir.add(r["sha256"])
        semua.append(r)

    print(f"dibuang karena hash kembar di dalam split: {kembar_akhir}")
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KOLOM)
        w.writeheader()
        w.writerows(semua)

    # Split: yang lama tetap, yang baru semua train.
    splits: dict[str, list[str]] = defaultdict(list)
    for r in semua:
        splits[r["split"]].append(r["clip_id"])
    stats = {
        "total": len(semua),
        "sumber": dict(Counter(r["source"] for r in semua)),
        "per_spesies": dict(Counter(r["species_scientific"] for r in semua)),
        "catatan": (
            "Split lama dipertahankan supaya angka uji bisa dibandingkan dengan "
            "baseline 0,6772. Semua data eksternal masuk train, tidak ada yang "
            "masuk val atau test."
        ),
    }
    with open(OUT_SPLITS, "w", encoding="utf-8") as f:
        json.dump({**splits, "stats": stats}, f, indent=2, ensure_ascii=False)

    print()
    print("manifest_v2         :", len(semua), "baris ->", OUT_MANIFEST)
    print("splits_v2           :", {k: len(v) for k, v in splits.items()})
    print("sumber              :", stats["sumber"])
    neg = stats["per_spesies"].get("_negative", 0)
    print("kelas _negative     :", neg)
    per_sp = {k: v for k, v in sorted(stats["per_spesies"].items()) if k != "_negative"}
    print("spesies target      :", len(per_sp))
    for k, v in per_sp.items():
        print(f"   {k:32s} {v}")


if __name__ == "__main__":
    main()
