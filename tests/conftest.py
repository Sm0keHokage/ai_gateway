import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "5")

import pytest
import pytest_asyncio
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.database import Base, get_db, get_session_maker
from app.db.repositories import ApiKeyRepository
from app.security import hash_key
from app.redis_client import get_redis
from app.dependencies import get_llm_router
from app.router import LLMRouter
from app.schema import LLMProvider, UsageInfo


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_maker(test_engine):
    return async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def fake_redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def api_key_raw(session_maker):
    raw = "unit-test-raw-key"
    async with session_maker() as session:
        async with session.begin():
            await ApiKeyRepository.create(
                session,
                key_hash=hash_key(raw),
                key_prefix=raw[:8],
                name="test-client",
                rate_limit_per_minute=None,
            )
    return raw


def make_mock_gateway(provider: LLMProvider) -> MagicMock:
    gateway = MagicMock()
    gateway.provider = provider
    gateway.default_model = f"{provider}-model"
    gateway.complete = AsyncMock(
        return_value=(
            f"Response from {provider}",
            UsageInfo(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            f"{provider}-model",
        )
    )
    gateway.health_check = AsyncMock(return_value=(True, None))
    return gateway


@pytest.fixture
def mock_llm_router():
    return LLMRouter(
        {
            LLMProvider.OPENAI: make_mock_gateway(LLMProvider.OPENAI),
            LLMProvider.ANTHROPIC: make_mock_gateway(LLMProvider.ANTHROPIC),
            LLMProvider.GEMINI: make_mock_gateway(LLMProvider.GEMINI),
        }
    )


@pytest_asyncio.fixture
async def client(session_maker, fake_redis, mock_llm_router):
    from main import app

    async def override_get_db():
        async with session_maker() as session:
            yield session

    async def override_get_redis():
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_maker] = lambda: session_maker
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_llm_router] = lambda: mock_llm_router

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
