"""Langkah 2: masukkan kondisi lapangan ke data latih, sekaligus sisihkan klip ND.

Yang dilakukan:
  1. Klip berlisensi ND (no derivatives) dikeluarkan dari data, karena pipeline ini
     memotong klip dan melatih model dengannya.
  2. Klip latih yang tersisa dibuatkan tiga variasi kondisi lapangan memakai
     parameter ffmpeg yang sama dengan ml/degradation.py, jadi simulasi latih dan
     simulasi uji konsisten.
  3. Embedding dihitung untuk klip tambahan itu, lalu digabung dengan embedding
     bersih yang sudah ada.
  4. Model dilatih ulang dengan konfigurasi yang sama dengan model produksi
     (300 epoch, hidden 256, lr 0.001, seed 42), hanya data latihnya yang berubah.
     Data validasi dan uji tetap bersih, supaya angkanya bisa dibandingkan langsung.

Hasilnya tidak menimpa model produksi: tersimpan di ml/checkpoints_aug/.

Pakai:
    cd ml && ../.venv/bin/python augment_train.py
    cd ml && ../.venv/bin/python augment_train.py --tanpa-augmentasi   # hanya sisihkan ND
"""
import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).resolve().parent
DATA_DIR = ML_DIR / "data"
REPO_DIR = ML_DIR.parent
sys.path.insert(0, str(DATA_DIR))
sys.path.insert(0, str(ML_DIR))
sys.path.insert(0, str(REPO_DIR))

import degradation as deg  # noqa: E402
import extract_embeddings as ee  # noqa: E402
import train as train_mod  # noqa: E402

AUG_DIR = DATA_DIR / "augmented"
EMB_AUG = ML_DIR / "embeddings_aug"
CKPT_AUG = ML_DIR / "checkpoints_aug"
SPLITS_AUG = DATA_DIR / "splits_aug.json"
TIER_LATIH = ["hujan_deras", "kota", "jarak_30m"]
# Model hanya membaca 3 detik pertama klip (extract_embeddings.load_audio), jadi klip
# simulasi dipotong ke durasi itu. Kalau tidak, folder data latih membengkak 10x.
DURASI_LATIH = 3.0


def lisensi_nd(lic: str) -> bool:
    return "nd" in (lic or "").lower()


def bangun_audio_latih(rows: list[dict], tier_nama: list[str]) -> dict[str, list[dict]]:
    """Buat variasi kondisi lapangan untuk tiap klip latih."""
    hasil: dict[str, list[dict]] = {}
    for nama in tier_nama:
        tier = deg.TIERS[nama]
        folder = AUG_DIR / nama
        folder.mkdir(parents=True, exist_ok=True)
        daftar = []
        for rec in rows:
            sumber = DATA_DIR / rec["local_path"]
            if not sumber.exists():
                continue
            tujuan = folder / f"{rec['clip_id']}.wav"
            if not tujuan.exists():
                perintah = deg.bangun_perintah(sumber, tujuan, tier, deg.rms_berkas(sumber),
                                               batas_detik=DURASI_LATIH)
                proses = subprocess.run(perintah, capture_output=True, text=True)
                if proses.returncode != 0:
                    print(f"    gagal {rec['clip_id']} / {nama}: {proses.stderr.strip()[:70]}")
                    continue
            daftar.append({
                "clip_id": f"{rec['clip_id']}-{nama}",
                "species_scientific": rec["species_scientific"],
                "local_path": str(tujuan.relative_to(DATA_DIR)),
            })
        hasil[nama] = daftar
        print(f"  {nama}: {len(daftar)} klip latih")
    return hasil


def embedding_untuk(rows: list[dict], interp) -> tuple[np.ndarray, np.ndarray, list[str]]:
    fitur, label, ids = [], [], []
    label_map = json.loads((ML_DIR / "embeddings" / "label_map.json").read_text())
    for rec in rows:
        berkas = DATA_DIR / rec["local_path"]
        if not berkas.exists():
            continue
        kelas = label_map.get(rec["species_scientific"])
        if kelas is None:
            continue
        try:
            audio = ee.load_audio(str(berkas))
            fitur.append(ee.extract_birdnet_embedding(interp, audio))
        except Exception as exc:
            print(f"    gagal embed {berkas.name}: {str(exc)[:60]}")
            continue
        label.append(kelas)
        ids.append(rec["clip_id"])
    if not fitur:
        return np.zeros((0, ee.EMBEDDING_DIM), dtype=np.float32), np.array([], dtype=int), []
    return np.vstack(fitur).astype(np.float32), np.array(label, dtype=int), ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tanpa-augmentasi", action="store_true",
                        help="hanya sisihkan klip ND, tanpa menambah data simulasi")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--lewati-latih", action="store_true", help="siapkan data saja")
    args = parser.parse_args()

    rows = list(csv.DictReader((DATA_DIR / "manifest.csv").open()))
    splits = json.loads((DATA_DIR / "splits.json").read_text())

    bersih = [r for r in rows if not lisensi_nd(r.get("license", ""))]
    nd = len(rows) - len(bersih)
    print(f"klip total {len(rows)}, dibuang karena ND {nd}, tersisa {len(bersih)}")

    id_bersih = {r["clip_id"] for r in bersih}
    id_latih = [c for c in splits["train"] if c in id_bersih]
    id_val = [c for c in splits["val"] if c in id_bersih]
    id_uji = [c for c in splits["test"] if c in id_bersih]
    print(f"split bersih: latih {len(id_latih)}, val {len(id_val)}, uji {len(id_uji)}")

    # Embedding bersih: ambil barisnya dari cache yang sudah ada.
    emb = np.load(ML_DIR / "embeddings" / "embeddings.npy")
    lab = np.load(ML_DIR / "embeddings" / "labels.npy")
    cids = json.loads((ML_DIR / "embeddings" / "clip_ids.json").read_text())
    posisi = {c: i for i, c in enumerate(cids)}

    semua_id = list(id_latih) + list(id_val) + list(id_uji)
    X_bersih = np.vstack([emb[posisi[c]] for c in semua_id if c in posisi])
    y_bersih = np.array([lab[posisi[c]] for c in semua_id if c in posisi], dtype=int)
    id_bersih_final = [c for c in semua_id if c in posisi]

    id_tambahan: list[str] = []
    X_tambahan = np.zeros((0, ee.EMBEDDING_DIM), dtype=np.float32)
    y_tambahan = np.array([], dtype=int)

    if not args.tanpa_augmentasi:
        rows_latih = [r for r in bersih if r["clip_id"] in set(id_latih)]
        print(f"membuat variasi kondisi lapangan untuk {len(rows_latih)} klip latih:")
        hasil = bangun_audio_latih(rows_latih, TIER_LATIH)
        semua_tambahan = [rec for daftar in hasil.values() for rec in daftar]
        print(f"menghitung embedding {len(semua_tambahan)} klip tambahan:")
        interp = ee.create_interpreter(ee.get_birdnet_model_path())
        X_tambahan, y_tambahan, id_tambahan = embedding_untuk(semua_tambahan, interp)
        print(f"  embedding tambahan: {X_tambahan.shape}")

    EMB_AUG.mkdir(parents=True, exist_ok=True)
    if len(X_tambahan):
        X_gabung = np.vstack([X_bersih, X_tambahan])
        y_gabung = np.concatenate([y_bersih, y_tambahan])
        id_gabung = id_bersih_final + id_tambahan
    else:
        X_gabung, y_gabung, id_gabung = X_bersih, y_bersih, id_bersih_final

    np.save(EMB_AUG / "embeddings.npy", X_gabung)
    np.save(EMB_AUG / "labels.npy", y_gabung)
    (EMB_AUG / "clip_ids.json").write_text(json.dumps(id_gabung))
    shutil.copy(ML_DIR / "embeddings" / "label_map.json", EMB_AUG / "label_map.json")

    SPLITS_AUG.write_text(json.dumps({
        "train": id_latih + id_tambahan,
        "val": id_val,
        "test": id_uji,
    }, indent=2))
    print(f"data latih baru: {len(id_latih) + len(id_tambahan)} klip "
          f"(bersih {len(id_latih)} + simulasi {len(id_tambahan)})")

    if args.lewati_latih:
        print("latih dilewati atas permintaan")
        return 0

    CKPT_AUG.mkdir(parents=True, exist_ok=True)
    train_mod.EMB_DIR = EMB_AUG
    train_mod.SPLITS_FILE = SPLITS_AUG
    train_mod.CHECKPOINT_DIR = CKPT_AUG
    sys.argv = ["train.py", "--epochs", str(args.epochs), "--hidden", "256",
                "--lr", "0.001", "--seed", str(args.seed)]
    print("melatih ulang dengan data latih yang sudah memuat kondisi lapangan")
    train_mod.main()
    (CKPT_AUG / "catatan.json").write_text(json.dumps({
        "klip_nd_dibuang": nd,
        "klip_latih_bersih": len(id_latih),
        "klip_simulasi": len(id_tambahan),
        "tier_simulasi": TIER_LATIH,
        "epochs": args.epochs,
        "seed": args.seed,
        "label_map": "sama dengan ml/embeddings/label_map.json",
        "catatan": "Model ini hasil langkah 2: klip ND disisihkan dan kondisi "
                   "lapangan simulasi masuk ke data latih. Validasi dan uji tetap bersih.",
    }, indent=2, ensure_ascii=False))
    print(f"selesai. checkpoint: {CKPT_AUG.relative_to(REPO_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
