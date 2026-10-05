"""Token revocation dan pembatas percobaan login.

Dua hal yang dijaga di sini:
1. Logout benar-benar mematikan token. JWT bersifat stateless, jadi id token (jti)
   yang sudah keluar dicatat di Redis sampai masa berlakunya habis.
2. Login dibatasi per alamat email dan alamat IP, supaya tidak bisa ditebak
   berulang kali tanpa henti.
"""
import time

import redis.asyncio as aioredis
from jose import jwt

from app.config import get_settings

settings = get_settings()

LOGIN_LIMIT = 5
LOGIN_WINDOW_SECONDS = 60
REVOKED_PREFIX = "gemahutan:revoked:"
LOGIN_PREFIX = "gemahutan:login:"


def _client() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url)


async def revoke_token(token: str) -> bool:
    """Catat jti token sebagai dicabut sampai token itu kedaluwarsa sendiri."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
    except Exception:
        return False

    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti:
        return False

    ttl = max(1, int(exp - time.time())) if exp else settings.jwt_refresh_token_expire_days * 86400
    try:
        client = _client()
        await client.setex(f"{REVOKED_PREFIX}{jti}", ttl, "1")
        await client.aclose()
        return True
    except Exception:
        # Redis mati: jangan gagalkan logout, tapi token tidak tercabut.
        return False


async def is_token_revoked(payload: dict) -> bool:
    jti = payload.get("jti")
    if not jti:
        return False
    try:
        client = _client()
        found = await client.exists(f"{REVOKED_PREFIX}{jti}")
        await client.aclose()
        return bool(found)
    except Exception:
        # Redis tidak bisa memastikan status pencabutan. Tolak token agar
        # gangguan dependensi tidak berubah menjadi bypass autentikasi.
        return True


async def register_login_failure(identifier: str) -> int:
    key = f"{LOGIN_PREFIX}{identifier}"
    try:
        client = _client()
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, LOGIN_WINDOW_SECONDS)
        await client.aclose()
        return int(count)
    except Exception:
        return 0


async def login_blocked_for(identifier: str) -> int:
    """Kembalikan sisa detik blokir. 0 berarti tidak diblokir."""
    key = f"{LOGIN_PREFIX}{identifier}"
    try:
        client = _client()
        count = await client.get(key)
        if not count or int(count) < LOGIN_LIMIT:
            await client.aclose()
            return 0
        ttl = await client.ttl(key)
        await client.aclose()
        return max(1, int(ttl))
    except Exception:
        return 0


async def clear_login_failures(identifier: str) -> None:
    try:
        client = _client()
        await client.delete(f"{LOGIN_PREFIX}{identifier}")
        await client.aclose()
    except Exception:
        pass


def login_identifier(email: str, ip: str | None) -> str:
    return f"{email.strip().lower()}|{ip or 'tanpa-ip'}"
