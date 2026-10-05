from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

async_engine = create_async_engine(settings.database_url, echo=False, pool_size=10)
async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)

sync_engine = create_engine(settings.database_url_sync, echo=False)


async def get_async_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
