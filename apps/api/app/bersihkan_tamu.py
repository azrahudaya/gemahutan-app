"""Hapus akun tamu lama beserta rekamannya. Dijalankan cron di server:

    docker compose exec -T api python -m app.bersihkan_tamu
"""

import asyncio

from app.config import get_settings
from app.database import async_session_factory
from app.services import tamu


async def utama() -> None:
    async with async_session_factory() as db:
        hasil = await tamu.bersihkan(db, umur_jam=get_settings().tamu_umur_jam)
    print(f"Tamu dibersihkan: {hasil['akun']} akun, {hasil['rekaman']} rekaman")


if __name__ == "__main__":
    asyncio.run(utama())
