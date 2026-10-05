"""Isi data demo dari klip Xeno-canto asli yang ikut di repo.

Beda dengan data demo lama yang cuma baris DB tanpa berkas audio, script ini
benar-benar mengunggah audio ke MinIO lalu memasukkan job ke antrean supaya
worker memprosesnya seperti unggahan pengguna. Hasil deteksi dan indeks yang
muncul di dashboard karenanya hasil hitung nyata.

Pakai:
    docker compose exec api python -m app.seed_demo            # tambah 8 rekaman demo
    docker compose exec api python -m app.seed_demo --purge    # hapus dulu data demo lama
    docker compose exec api python -m app.seed_demo --purge-orphans
        # hapus SEMUA baris recording yang berkas audionya tidak ada di storage
"""
import argparse
import asyncio
import csv
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from app.database import async_session_factory
from app.models.tables import Job, JobStatus, Recording, RecordingStatus
from app.services.queue import enqueue_job
from app.services.storage import ensure_bucket, object_exists, upload_fileobj

ML_DIR = Path(os.getenv("ML_DIR", "/app/ml"))
DEMO_DIR = ML_DIR / "demo_audio"
LEGACY_DEMO_PREFIX = "demo/"


def load_manifest() -> list[dict]:
    csv_path = DEMO_DIR / "ATTRIBUTION.csv"
    if not csv_path.exists():
        return []
    with open(csv_path) as f:
        return list(csv.DictReader(f))


async def purge_legacy_demo(session) -> int:
    """Hapus baris demo lama yang menunjuk berkas audio tidak ada."""
    rows = await session.execute(
        text("SELECT id, storage_key FROM recordings WHERE storage_key LIKE :p"),
        {"p": f"{LEGACY_DEMO_PREFIX}%"},
    )
    targets = [r[0] for r in rows.all()]
    if targets:
        await session.execute(text("DELETE FROM detections WHERE recording_id = ANY(:ids)"), {"ids": targets})
        await session.execute(text("DELETE FROM acoustic_indices WHERE recording_id = ANY(:ids)"), {"ids": targets})
        await session.execute(text("DELETE FROM jobs WHERE recording_id = ANY(:ids)"), {"ids": targets})
        await session.execute(text("DELETE FROM recordings WHERE id = ANY(:ids)"), {"ids": targets})
        await session.commit()
    return len(targets)


async def purge_orphans(session) -> int:
    """Hapus baris recording yang audionya tidak ada di MinIO."""
    rows = await session.execute(text("SELECT id, storage_key FROM recordings"))
    orphans = [r[0] for r in rows.all() if not object_exists(r[1])]
    if orphans:
        await session.execute(text("DELETE FROM detections WHERE recording_id = ANY(:ids)"), {"ids": orphans})
        await session.execute(text("DELETE FROM acoustic_indices WHERE recording_id = ANY(:ids)"), {"ids": orphans})
        await session.execute(text("DELETE FROM jobs WHERE recording_id = ANY(:ids)"), {"ids": orphans})
        await session.execute(text("DELETE FROM recordings WHERE id = ANY(:ids)"), {"ids": orphans})
        await session.commit()
    return len(orphans)


async def seed_demo(limit: int | None, purge: bool, purge_orphans_flag: bool) -> None:
    manifest = load_manifest()
    if not manifest:
        print(f"Tidak ada klip demo di {DEMO_DIR}. Jalankan `make download` lalu ulangi.")
        return
    if limit:
        manifest = manifest[:limit]

    ensure_bucket()

    async with async_session_factory() as session:
        if purge:
            removed = await purge_legacy_demo(session)
            print(f"Purge data demo lama (storage_key '{LEGACY_DEMO_PREFIX}'): {removed} baris")
        if purge_orphans_flag:
            removed = await purge_orphans(session)
            print(f"Purge baris tanpa berkas audio: {removed} baris")

        admin = (
            await session.execute(text("SELECT id FROM users ORDER BY id LIMIT 1"))
        ).scalar()
        if not admin:
            print("Belum ada user. Jalankan `python -m app.seed` dulu.")
            return

        sites = [
            r[0]
            for r in (
                await session.execute(text("SELECT id FROM sites ORDER BY id"))
            ).all()
        ]
        if not sites:
            print("Belum ada lokasi. Jalankan `python -m app.seed` dulu.")
            return

        inserted = skipped = 0
        queued_ids = []

        for idx, row in enumerate(manifest):
            src = DEMO_DIR / row["file"]
            if not src.exists():
                print(f"Lewati {row['file']}: berkas tidak ada")
                continue

            key = f"recordings/{uuid.uuid4().hex}.mp3"
            with open(src, "rb") as fh:
                upload_fileobj(fh, key, content_type="audio/mpeg")

            recorded_at = datetime.now(UTC) - timedelta(days=(idx % 5) + 1,
                                                                 hours=idx)
            recording = Recording(
                site_id=sites[idx % len(sites)],
                uploaded_by=admin,
                storage_key=key,
                recorded_at=recorded_at,
                status=RecordingStatus.pending,
            )
            session.add(recording)
            await session.flush()

            session.add(Job(recording_id=recording.id, status=JobStatus.pending))
            await session.commit()

            try:
                await enqueue_job(recording.id)
                queued_ids.append(recording.id)
            except Exception as exc:
                print(f"Rekaman {recording.id} tersimpan tapi gagal masuk antrean: {exc}")

            inserted += 1
            print(
                f"[{idx + 1}/{len(manifest)}] {row['species_scientific']} "
                f"({src.name}, {row['duration_s']}) -> recording id {recording.id}"
            )

        print(
            f"\nSelesai. {inserted} rekaman demo diunggah, {skipped} dilewati, "
            f"{len(queued_ids)} masuk antrean worker."
        )
        print("Data demo berasal dari klip Xeno-canto asli, lihat ml/demo_audio/ATTRIBUTION.csv.")


def main():
    parser = argparse.ArgumentParser(description="Seeding data demo dari klip nyata")
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah klip")
    parser.add_argument("--purge", action="store_true", help="Hapus data demo lama dulu")
    parser.add_argument(
        "--purge-orphans",
        action="store_true",
        dest="purge_orphans",
        help="Hapus semua recording yang berkas audionya tidak ada di storage",
    )
    args = parser.parse_args()
    asyncio.run(seed_demo(args.limit, args.purge, args.purge_orphans))


if __name__ == "__main__":
    main()
