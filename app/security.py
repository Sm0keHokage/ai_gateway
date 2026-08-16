import hashlib
import logging
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ApiKey
from app.db.repositories import ApiKeyRepository

logger = logging.getLogger(__name__)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def verify_api_key(
    key: str = Security(api_key_header),
    session: AsyncSession = Depends(get_db),
) -> ApiKey:

    api_key = await ApiKeyRepository.get_by_hash(session, hash_key(key))

    if not api_key or not api_key.is_active:
        raise HTTPException(
            status_code=403,
            detail="Invalid or inactive API key",
        )

    return api_key
