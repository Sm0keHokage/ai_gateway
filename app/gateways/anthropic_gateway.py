from typing import Dict, List, Optional, Tuple
import aiohttp

from app.gateways.retry import with_retry
from app.schema import LLMProvider, Message, MessageRole, UsageInfo
from app.exceptions import (
    GatewayError,
    GatewayTimeoutError,
    GatewayRateLimitError,
)
from app.gateways.base import BaseLLMGateway


class AnthropicGateway(BaseLLMGateway):
    provider = LLMProvider.ANTHROPIC
    MAX_TEMPERATURE = 1.0
    ANTHROPIC_VERSION = "2023-06-01"

    def _get_headers(self) -> Dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    def _split_messages(self, messages: List[Message]) -> Tuple[Optional[str], List[Dict]]:
        system = None
        formatted = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system = msg.content
            else:
                formatted.append({"role": msg.role.value, "content": msg.content})
        return system, formatted

    DEFAULT_MAX_TOKENS = 8192

    @with_retry(max_attempts=3, min_wait=1.0, max_wait=8.0)
    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> Tuple[str, UsageInfo, str]:
        resolved_model = self._resolve_model(model)
        safe_temp = self._clamp_temperature(temperature)
        system, formatted_messages = self._split_messages(messages)

        payload = {
            "model": resolved_model,
            "messages": formatted_messages,
            "max_tokens": self.DEFAULT_MAX_TOKENS,
            "temperature": safe_temp,
        }
        if system:
            payload["system"] = system

        try:
            session = await self.get_session()
            async with session.post(
                f"{self.base_url}/messages",
                headers=self._get_headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                await self._raise_for_status(response)
                data = await response.json()

            content = data["content"][0]["text"]
            raw_usage = data.get("usage", {})
            usage = UsageInfo(
                prompt_tokens=raw_usage.get("input_tokens", 0),
                completion_tokens=raw_usage.get("output_tokens", 0),
                total_tokens=(raw_usage.get("input_tokens", 0) + raw_usage.get("output_tokens", 0)),
            )
            return content, usage, resolved_model

        except aiohttp.ServerTimeoutError:
            raise GatewayTimeoutError(
                f"Anthropic timeout after {self.timeout}s", provider=self.provider
            )

    async def health_check(self) -> Tuple[bool, Optional[str]]:
        try:
            session = await self.get_session()
            async with session.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                if response.status == 200:
                    return True, None
                return False, f"Status: {response.status}"
        except Exception as e:
            return False, str(e)

    async def _raise_for_status(self, response: aiohttp.ClientResponse):
        if response.status == 429:
            raise GatewayRateLimitError(
                "Anthropic rate limit exceeded", provider=self.provider, status_code=429
            )
        if response.status >= 400:
            text = await response.text()
            raise GatewayError(
                f"Anthropic error {response.status}: {text}",
                provider=self.provider,
                status_code=response.status,
            )
