from functools import lru_cache
import redis.asyncio as redis
from app.settings import settings


@lru_cache
def get_redis_pool() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> redis.Redis:
    return get_redis_pool()
