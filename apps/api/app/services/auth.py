from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import jwt
from passlib.hash import argon2

from app.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    return argon2.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return argon2.verify(password, password_hash)


def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int, role: str, version: int = 0) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        # jti dipakai supaya token bisa dicabut saat logout.
        "jti": uuid4().hex,
        # ver dibandingkan dengan users.token_version. Token dengan versi lama
        # ditolak, jadi menaikkan versi memutus semua sesi akun itu sekaligus.
        "ver": version,
        "iat": datetime.now(UTC),
        "exp": expire,
    }
    return _encode(payload)


def create_refresh_token(user_id: int, version: int = 0) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": uuid4().hex,
        # Sama seperti access token: versi lama ditolak setelah sandi diganti.
        "ver": version,
        "iat": datetime.now(UTC),
        "exp": expire,
    }
    return _encode(payload)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def token_masih_berlaku(payload: dict, token_version: int) -> bool:
    """True kalau versi token di JWT sama dengan versi yang berlaku sekarang.

    Dipakai jalur verifikasi token biasa dan jalur penukaran refresh token. Aturan
    ini ada di satu tempat karena kalau disalin ke dua tempat, cepat atau lambat
    salah satunya tertinggal saat aturannya berubah, dan celahnya justru lewat
    jalur yang terlupakan.

    Token tanpa klaim `ver` dianggap versi 0, sehingga token yang sudah beredar
    sebelum aturan ini dipasang tetap dilayani sampai akunnya mengatur ulang sandi.
    """
    return int(payload.get("ver", 0)) == int(token_version)
