"""Cetak empat nilai acak 32 byte untuk env produksi.

Dipakai untuk mengisi .env.prod sebelum deploy. Tidak menulis ke berkas,
hanya mencetak ke stdout, supaya operator memilih sendiri tempat
menyimpannya.

Cara pakai:
    python3 ops/generate_secrets.py
    python3 ops/generate_secrets.py >> .env.prod

Format setiap baris sesuai nama env produksi GemaHutan:
- JWT_SECRET : penanda sesi JWT (HS256)
- SECRET_KEY : penanda internal (Argon2 dan kriptografi lain)
- S3_ACCESS_KEY : kredensial MinIO / S3
- S3_SECRET_KEY : sandi MinIO / S3

Nilai ditulis dengan token_hex supaya 64 karakter ASCII aman untuk env
dan tidak perlu encode tambahan. Jangan pernah menulis dengan str() tanpa
encode, karena secrets.token_bytes menghasilkan bytes yang tidak bisa dicetak
mentah ke terminal.
"""
import secrets
import sys


def generate() -> dict[str, str]:
    """Kembalikan empat nilai acak 32 byte dalam hex (64 karakter ASCII)."""
    return {
        "JWT_SECRET": secrets.token_hex(32),
        "SECRET_KEY": secrets.token_hex(32),
        "S3_ACCESS_KEY": secrets.token_hex(16),
        "S3_SECRET_KEY": secrets.token_hex(32),
    }


def main() -> int:
    nilai = generate()
    out = sys.stdout
    for nama, isi in nilai.items():
        # token_hex() sudah mengembalikan str ASCII, jadi encode tidak
        # dibutuhkan. Tulis apa adanya ke stdout (encoding utf-8).
        out.write(f"{nama}={isi}\n")
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())