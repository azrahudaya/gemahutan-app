"""Queue service for enqueuing jobs."""
from arq.connections import ArqRedis, RedisSettings, create_pool

from app.config import get_settings

_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def enqueue_job(recording_id: int):
    pool = await get_arq_pool()
    await pool.enqueue_job("process_recording", recording_id)
