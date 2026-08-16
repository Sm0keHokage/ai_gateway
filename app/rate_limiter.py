import time
import logging
from fastapi import Depends, HTTPException
import redis.asyncio as redis

from app.db.models import ApiKey
from app.redis_client import get_redis
from app.security import verify_api_key
from app.settings import settings

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60


async def rate_limit(
    api_key: ApiKey = Depends(verify_api_key),
    redis_client: redis.Redis = Depends(get_redis),
) -> ApiKey:
    limit = api_key.rate_limit_per_minute or settings.RATE_LIMIT_PER_MINUTE
    window = int(time.time() // WINDOW_SECONDS)
    redis_key = f"rate_limit:{api_key.id}:{window}"

    count = await redis_client.incr(redis_key)
    if count == 1:
        # Ставим TTL только на первый запрос в окне, чтобы ключ сам исчез
        await redis_client.expire(redis_key, WINDOW_SECONDS)
    ttl = await redis_client.ttl(redis_key)

    if count > limit:
        retry_after = ttl if ttl > 0 else WINDOW_SECONDS
        logger.warning(
            f"[RATE LIMIT] key={api_key.key_prefix}... exceeded " f"{limit}/min (count={count})"
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {limit} requests per minute",
            headers={"Retry-After": str(retry_after)},
        )

    return api_key
