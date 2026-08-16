import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ApiKey, RequestLog


class ApiKeyRepository:

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        key_hash: str,
        key_prefix: str,
        name: str,
        rate_limit_per_minute: Optional[int] = None,
    ) -> ApiKey:
        api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        session.add(api_key)
        await session.flush()
        await session.refresh(api_key)
        return api_key

    @classmethod
    async def get_by_hash(cls, session: AsyncSession, key_hash: str) -> Optional[ApiKey]:
        result = await session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
        return result.scalar_one_or_none()

    @classmethod
    async def get_all(cls, session: AsyncSession) -> List[ApiKey]:
        result = await session.execute(select(ApiKey))
        return list(result.scalars().all())

    @classmethod
    async def set_active(
        cls, session: AsyncSession, key_id: uuid.UUID, is_active: bool
    ) -> Optional[ApiKey]:
        result = await session.execute(select(ApiKey).where(ApiKey.id == key_id))
        api_key = result.scalar_one_or_none()
        if not api_key:
            return None
        api_key.is_active = is_active
        await session.flush()
        await session.refresh(api_key)
        return api_key


class RequestLogRepository:

    @classmethod
    async def create(cls, session: AsyncSession, data: Dict[str, Any]) -> RequestLog:
        log = RequestLog(**data)
        session.add(log)
        await session.flush()
        return log
