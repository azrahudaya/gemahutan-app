"""Ubah deteksi yang sudah diverifikasi ahli menjadi bahan latih.

Alur:
1. Ambil deteksi berstatus benar (correct) dari database.
2. Unduh audio rekaman aslinya dari storage.
3. Potong segmen sesuai rentang deteksi, simpan sebagai klip 48 kHz mono.
4. Tulis ml/data/verified_manifest.csv dengan skema sama seperti manifest.csv.

Dengan begitu hasil verifikasi ahli benar-benar masuk ke jalur latih:
verifikasi -> klip -> embedding -> latih ulang classifier Track B.

Pakai (dari root repo, supaya klip tersimpan ke host):
    docker compose run --rm -v "$PWD/ml/data:/app/ml/data" api \\
        python ml/data/from_verifications.py --min-confidence 0.5 --status correct

Lalu latih ulang dengan menggabungkan manifest:
    docker compose run --rm -v "$PWD/ml/data:/app/ml/data" api \\
        python ml/data/from_verifications.py --merge
    make model
"""
import argparse
import csv
import hashlib
import os
import tempfile
from pathlib import Path

import boto3
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "verified"
OUT_MANIFEST = BASE_DIR / "verified_manifest.csv"
MAIN_MANIFEST = BASE_DIR / "manifest.csv"

SR = 48000
MIN_SEGMENT_SECONDS = 3.0
PAD_SECONDS = 0.5

FIELDNAMES = [
    "clip_id", "source", "source_url", "species_scientific", "species_common",
    "split", "duration_s", "sample_rate", "quality", "license", "sha256", "local_path",
]


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
        region_name=os.getenv("S3_REGION", "us-east-1"),
    )


def fetch_verified(status: str, min_confidence: float) -> list[dict]:
    engine = create_engine(os.environ["DATABASE_URL_SYNC"])
    sql = text(
        """
        SELECT d.id, d.recording_id, d.confidence, d.start_s, d.end_s,
               s.scientific_name, s.common_name_en,
               r.storage_key, r.recorded_at, r.site_id
        FROM detections d
        JOIN species s ON s.id = d.species_id
        JOIN recordings r ON r.id = d.recording_id
        WHERE d.verified_status = :status
          AND d.confidence >= :min_conf
          AND d.verified_status != 'unverified'
        ORDER BY d.id
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"status": status, "min_conf": min_confidence}).all()
    return [dict(r._mapping) for r in rows]


def cut_segment(s3, storage_key: str, start_s: float, end_s: float, dest: Path) -> tuple[float, int]:
    """Potong segmen dari audio di storage. Kembalikan durasi dan sample rate."""
    import librosa
    import soundfile as sf

    with tempfile.NamedTemporaryFile(suffix=Path(storage_key).suffix, delete=False) as tmp:
        tmp_path = tmp.name
    try:
        with open(tmp_path, "wb") as fh:
            s3.download_fileobj(os.getenv("S3_BUCKET", "gemahutan-audio"), storage_key, fh)

        start = max(0.0, float(start_s) - PAD_SECONDS)
        duration = max(MIN_SEGMENT_SECONDS, float(end_s) - float(start_s) + 2 * PAD_SECONDS)
        y, _ = librosa.load(tmp_path, sr=SR, mono=True, offset=start, duration=duration)
        if y.size == 0:
            raise ValueError("segmen kosong")

        dest.parent.mkdir(parents=True, exist_ok=True)
        sf.write(dest, y, SR)
        return len(y) / SR, SR
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(rows: list[dict]) -> None:
    with open(OUT_MANIFEST, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def merge_into_main() -> int:
    """Tambahkan klip terverifikasi ke manifest utama dan ke split latih.

    Splits wajib ikut diperbarui, kalau tidak klip barunya ada di manifest tapi
    tidak pernah dipakai saat latih (train.py memilih klip lewat splits.json).
    """
    if not OUT_MANIFEST.exists():
        print("verified_manifest.csv belum ada, jalankan tanpa --merge dulu")
        return 0

    existing_ids = set()
    existing_rows = []
    if MAIN_MANIFEST.exists():
        with open(MAIN_MANIFEST) as f:
            existing_rows = list(csv.DictReader(f))
            existing_ids = {r["clip_id"] for r in existing_rows}

    with open(OUT_MANIFEST) as f:
        verified_rows = [r for r in csv.DictReader(f) if r["clip_id"] not in existing_ids]

    if not verified_rows:
        print("Tidak ada klip terverifikasi baru untuk digabung")
        return 0

    with open(MAIN_MANIFEST, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(existing_rows)
        writer.writerows(verified_rows)

    splits_file = BASE_DIR / "splits.json"
    if splits_file.exists():
        import json
        splits = json.loads(splits_file.read_text())
        train_ids = splits.setdefault("train", [])
        added = [r["clip_id"] for r in verified_rows if r["clip_id"] not in train_ids]
        train_ids.extend(added)
        splits_file.write_text(json.dumps(splits, indent=2))
        print(f"{len(added)} klip ditambahkan ke split train")

    print(f"{len(verified_rows)} klip terverifikasi ditambahkan ke {MAIN_MANIFEST.name}")
    print("Jalankan `make model` untuk ekstraksi embedding dan latih ulang.")
    return len(verified_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deteksi terverifikasi jadi bahan latih")
    parser.add_argument("--status", default="correct", choices=["correct", "incorrect", "uncertain"])
    parser.add_argument("--min-confidence", type=float, default=0.0,
                        help="Abaikan deteksi di bawah nilai ini")
    parser.add_argument("--merge", action="store_true",
                        help="Gabungkan hasil ke ml/data/manifest.csv")
    args = parser.parse_args()

    if args.merge:
        merge_into_main()
        return

    rows = fetch_verified(args.status, args.min_confidence)
    if not rows:
        print(
            f"Belum ada deteksi berstatus '{args.status}' dengan confidence minimal "
            f"{args.min_confidence}. Verifikasi dulu di halaman detail rekaman."
        )
        return

    print(f"{len(rows)} deteksi terverifikasi akan dijadikan klip latih")
    s3 = s3_client()
    out_rows = []
    failed = 0

    for row in rows:
        clip_id = f"ver-{row['id']}"
        species_dir = row["scientific_name"].replace(" ", "_")
        dest = OUT_DIR / species_dir / f"{clip_id}.wav"
        try:
            duration, sample_rate = cut_segment(
                s3, row["storage_key"], row["start_s"], row["end_s"], dest
            )
        except Exception as exc:
            print(f"  gagal {clip_id}: {exc}")
            failed += 1
            continue

        out_rows.append({
            "clip_id": clip_id,
            "source": "human-verified",
            "source_url": f"internal://recording/{row['recording_id']}",
            "species_scientific": row["scientific_name"],
            "species_common": row["common_name_en"] or "",
            "split": "",
            "duration_s": f"{duration:.2f}",
            "sample_rate": sample_rate,
            "quality": f"verified-{row['confidence']:.2f}",
            "license": "internal",
            "sha256": sha256(dest),
            "local_path": str(dest.relative_to(BASE_DIR)),
        })
        print(f"  {clip_id} {row['scientific_name']} {duration:.1f}s confidence {row['confidence']:.2f}")

    write_manifest(out_rows)
    print(f"\n{len(out_rows)} klip tersimpan di {OUT_DIR}")
    print(f"Manifest: {OUT_MANIFEST.name}, gagal: {failed}")
    print("Langkah berikut: jalankan ulang dengan --merge, lalu `make model`.")


if __name__ == "__main__":
    main()
