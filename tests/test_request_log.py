import pytest
from sqlalchemy import select

from app.db.models import RequestLog


@pytest.mark.asyncio
async def test_successful_request_is_logged(client, session_maker, api_key_raw):
    response = await client.post(
        "/api/v1/complete",
        headers={"X-API-Key": api_key_raw},
        json={"messages": [{"role": "user", "content": "hi"}], "provider": "openai"},
    )
    assert response.status_code == 200

    async with session_maker() as session:
        logs = (await session.execute(select(RequestLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].success is True
    assert logs[0].status_code == 200
    assert logs[0].provider == "openai"


@pytest.mark.asyncio
async def test_failed_request_is_still_logged(client, session_maker, api_key_raw, mock_llm_router):
    """
    Регрессия: лог должен коммититься независимо от исхода запроса, а не
    теряться вместе с откатом транзакции при HTTPException.
    """
    from app.exceptions import GatewayError

    mock_llm_router._gateways["openai"].complete.side_effect = GatewayError(
        "boom", provider="openai", status_code=500
    )

    response = await client.post(
        "/api/v1/complete",
        headers={"X-API-Key": api_key_raw},
        json={"messages": [{"role": "user", "content": "hi"}], "provider": "openai"},
    )
    assert response.status_code == 502

    async with session_maker() as session:
        logs = (await session.execute(select(RequestLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].success is False
    assert logs[0].status_code == 502
    assert logs[0].error is not None
