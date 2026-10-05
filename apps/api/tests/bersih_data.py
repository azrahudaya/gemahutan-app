"""Pembersih data uji.

Test API berjalan di database yang sama dengan data demo, jadi akun, lokasi, dan
perangkat hasil pengujian harus dibuang sendiri setelah sesi selesai. Tanpa itu
halaman Pengguna terisi baris sampah setiap kali test dijalankan, dan itu terlihat
siapa pun yang membuka aplikasi.

Pembersihan ini bersandar pada awalan nama yang disepakati di test:
akun uji memakai email berawalan `test-`, `fase2-`, `uji-`, `reset-`, atau
`revoke-`, lokasi uji bernama
`Lokasi Uji ...`, dan perangkat uji bernama `Perangkat ...`. Mengubah awalan itu
di test berarti harus mengubah daftar di bawah juga.
"""
from __future__ import annotations

import os
from typing import Any

PREFIKS_EMAIL = ("test-%", "fase2-%", "uji%", "reset-%", "revoke-%")
PREFIKS_NAMA_LOKASI = "Lokasi Uji%"
PREFIKS_NAMA_PERANGKAT = "Perangkat %"


def _dsn(dsn: str | None) -> str:
    nilai = dsn or os.environ.get("DATABASE_URL_SYNC") or ""
    if not nilai:
        raise RuntimeError(
            "DATABASE_URL_SYNC tidak ada, pembersihan data uji tidak bisa jalan"
        )
    return nilai


def _buang_objek(storage_keys: list[str]) -> int:
    """Hapus berkas audio dan cache spektrogram milik rekaman uji di MinIO."""
    if not storage_keys:
        return 0
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        return 0

    endpoint = os.environ.get("S3_ENDPOINT")
    bucket = os.environ.get("S3_BUCKET")
    if not endpoint or not bucket:
        return 0

    klien = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY"),
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=Config(s3={"addressing_style": "path"}),
    )

    dibuang = 0
    for key in storage_keys:
        for kandidat in (key, f"cache/spectrogram/{key}.png"):
            try:
                klien.delete_object(Bucket=bucket, Key=kandidat)
                dibuang += 1
            except Exception:
                # Objek yang memang tidak ada bukan masalah pembersihan.
                continue
    return dibuang


def bersihkan(dsn: str | None = None, hapus_objek: bool = True) -> dict[str, Any]:
    """Buang seluruh baris hasil pengujian. Aman dipanggil berulang."""
    import psycopg

    laporan: dict[str, Any] = {
        "akun": 0,
        "rekaman": 0,
        "lokasi": 0,
        "perangkat": 0,
        "objek_minio": 0,
    }

    with psycopg.connect(_dsn(dsn)) as con:
        with con.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email LIKE ANY(%s)", (list(PREFIKS_EMAIL),))
            id_akun = [r[0] for r in cur.fetchall()]

            cur.execute(
                """
                SELECT id, storage_key FROM recordings
                WHERE uploaded_by = ANY(%s)
                   OR device_id IN (
                        SELECT id FROM devices WHERE name LIKE %s
                   )
                """,
                (id_akun, PREFIKS_NAMA_PERANGKAT),
            )
            rekaman = cur.fetchall()
            id_rekaman = [r[0] for r in rekaman]

            if id_rekaman:
                for tabel in ("detections", "acoustic_indices", "jobs"):
                    cur.execute(
                        f"DELETE FROM {tabel} WHERE recording_id = ANY(%s)", (id_rekaman,)
                    )
                cur.execute("DELETE FROM recordings WHERE id = ANY(%s)", (id_rekaman,))
                laporan["rekaman"] = cur.rowcount

            cur.execute(
                """
                DELETE FROM devices
                WHERE name LIKE %s
                   OR site_id IN (
                        SELECT id FROM sites
                        WHERE owner_id = ANY(%s) OR name LIKE %s
                   )
                """,
                (PREFIKS_NAMA_PERANGKAT, id_akun, PREFIKS_NAMA_LOKASI),
            )
            laporan["perangkat"] = cur.rowcount

            # Lokasi hanya dibuang kalau tidak ada rekaman yang masih menunjuk ke sana.
            cur.execute(
                """
                DELETE FROM sites
                WHERE (owner_id = ANY(%s) OR name LIKE %s)
                  AND id NOT IN (SELECT DISTINCT site_id FROM recordings)
                """,
                (id_akun, PREFIKS_NAMA_LOKASI),
            )
            laporan["lokasi"] = cur.rowcount

            if id_akun:
                cur.execute("DELETE FROM users WHERE id = ANY(%s)", (id_akun,))
                laporan["akun"] = cur.rowcount

        if hapus_objek:
            laporan["objek_minio"] = _buang_objek([r[1] for r in rekaman])

    return laporan
