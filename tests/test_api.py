import pytest


@pytest.mark.asyncio
async def test_complete_endpoint(client, api_key_raw):
    response = await client.post(
        "/api/v1/complete",
        headers={"X-API-Key": api_key_raw},
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "provider": "openai",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert data["provider"] == "openai"


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "providers" in data


@pytest.mark.asyncio
async def test_missing_api_key(client):
    response = await client.post(
        "/api/v1/complete",
        json={"messages": [{"role": "user", "content": "Hi"}]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_key(client):
    response = await client.post(
        "/api/v1/complete",
        headers={"X-API-Key": "does-not-exist"},
        json={"messages": [{"role": "user", "content": "Hi"}]},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_revoked_api_key_rejected(client, session_maker, api_key_raw):
    from app.db.repositories import ApiKeyRepository
    from app.security import hash_key

    async with session_maker() as session:
        async with session.begin():
            api_key = await ApiKeyRepository.get_by_hash(session, hash_key(api_key_raw))
            await ApiKeyRepository.set_active(session, api_key.id, False)

    response = await client.post(
        "/api/v1/complete",
        headers={"X-API-Key": api_key_raw},
        json={"messages": [{"role": "user", "content": "Hi"}]},
    )
    assert response.status_code == 403
