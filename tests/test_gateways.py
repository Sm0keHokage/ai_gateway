import pytest
from unittest.mock import MagicMock

from app.gateways.openai_gateway import OpenAIGateway
from app.gateways.anthropic_gateway import AnthropicGateway
from app.gateways.gemini_gateway import GeminiGateway
from app.exceptions import GatewayRateLimitError, GatewayError
from app.schema import Message, MessageRole


def make_gateway(cls):
    return cls(api_key="k", base_url="https://example.test", default_model="model-x")


def test_openai_clamps_temperature():
    gw = make_gateway(OpenAIGateway)
    assert gw._clamp_temperature(3.5) == 2.0
    assert gw._clamp_temperature(0.5) == 0.5


def test_anthropic_clamps_temperature_lower_max():
    gw = make_gateway(AnthropicGateway)
    assert gw._clamp_temperature(1.5) == 1.0


def test_anthropic_always_sends_max_tokens_without_user_input():
    gw = make_gateway(AnthropicGateway)
    payload = {
        "model": "model-x",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": gw.DEFAULT_MAX_TOKENS,
        "temperature": 0.7,
    }
    assert payload["max_tokens"] == 8192


def test_gemini_payload_has_no_max_tokens_cap():
    gw = make_gateway(GeminiGateway)
    payload = gw._build_payload([Message(role=MessageRole.USER, content="hi")], 0.7)
    assert "maxOutputTokens" not in payload["generationConfig"]


@pytest.mark.asyncio
async def test_openai_raises_rate_limit_error_on_429():
    gw = make_gateway(OpenAIGateway)
    response = MagicMock()
    response.status = 429
    with pytest.raises(GatewayRateLimitError):
        await gw._raise_for_status(response)


@pytest.mark.asyncio
async def test_openai_raises_gateway_error_on_500():
    gw = make_gateway(OpenAIGateway)
    response = MagicMock()
    response.status = 500

    async def text():
        return "internal error"

    response.text = text

    with pytest.raises(GatewayError):
        await gw._raise_for_status(response)
