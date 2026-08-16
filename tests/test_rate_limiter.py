import pytest


@pytest.mark.asyncio
async def test_allows_up_to_limit_then_429(client, api_key_raw):
    for i in range(5):
        response = await client.post(
            "/api/v1/complete",
            headers={"X-API-Key": api_key_raw},
            json={"messages": [{"role": "user", "content": f"msg {i}"}], "provider": "openai"},
        )
        assert response.status_code == 200, f"request {i} should pass"

    response = await client.post(
        "/api/v1/complete",
        headers={"X-API-Key": api_key_raw},
        json={"messages": [{"role": "user", "content": "one too many"}], "provider": "openai"},
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert "5 requests per minute" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rate_limit_is_per_api_key(client, session_maker):
    from app.db.repositories import ApiKeyRepository
    from app.security import hash_key

    raw_a, raw_b = "key-a-raw", "key-b-raw"
    async with session_maker() as session:
        async with session.begin():
            await ApiKeyRepository.create(session, hash_key(raw_a), raw_a[:8], "client-a")
            await ApiKeyRepository.create(session, hash_key(raw_b), raw_b[:8], "client-b")

    for _ in range(5):
        r = await client.post(
            "/api/v1/complete",
            headers={"X-API-Key": raw_a},
            json={"messages": [{"role": "user", "content": "hi"}], "provider": "openai"},
        )
        assert r.status_code == 200

    exhausted = await client.post(
        "/api/v1/complete",
        headers={"X-API-Key": raw_a},
        json={"messages": [{"role": "user", "content": "hi"}], "provider": "openai"},
    )
    assert exhausted.status_code == 429

    still_fresh = await client.post(
        "/api/v1/complete",
        headers={"X-API-Key": raw_b},
        json={"messages": [{"role": "user", "content": "hi"}], "provider": "openai"},
    )
    assert still_fresh.status_code == 200


@pytest.mark.asyncio
async def test_custom_per_key_rate_limit(client, session_maker):
    from app.db.repositories import ApiKeyRepository
    from app.security import hash_key

    raw = "custom-limit-key"
    async with session_maker() as session:
        async with session.begin():
            await ApiKeyRepository.create(
                session, hash_key(raw), raw[:8], "vip", rate_limit_per_minute=2
            )

    for _ in range(2):
        r = await client.post(
            "/api/v1/complete",
            headers={"X-API-Key": raw},
            json={"messages": [{"role": "user", "content": "hi"}], "provider": "openai"},
        )
        assert r.status_code == 200

    r = await client.post(
        "/api/v1/complete",
        headers={"X-API-Key": raw},
        json={"messages": [{"role": "user", "content": "hi"}], "provider": "openai"},
    )
    assert r.status_code == 429
