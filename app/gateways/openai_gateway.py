from typing import Dict, List, Optional, Tuple
import aiohttp

from app.gateways.retry import with_retry
from app.schema import LLMProvider, Message, UsageInfo
from app.exceptions import (
    GatewayError,
    GatewayTimeoutError,
    GatewayRateLimitError,
)
from app.gateways.base import BaseLLMGateway


class OpenAIGateway(BaseLLMGateway):
    provider = LLMProvider.OPENAI
    MAX_TEMPERATURE = 2.0

    def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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

        payload = {
            "model": resolved_model,
            "messages": self._format_messages(messages),
            "temperature": safe_temp,
        }

        try:
            session = await self.get_session()
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            ) as response:
                await self._raise_for_status(response)
                data = await response.json()

            content = data["choices"][0]["message"]["content"]
            raw_usage = data.get("usage", {})
            usage = UsageInfo(
                prompt_tokens=raw_usage.get("prompt_tokens", 0),
                completion_tokens=raw_usage.get("completion_tokens", 0),
                total_tokens=raw_usage.get("total_tokens", 0),
            )
            return content, usage, resolved_model

        except aiohttp.ServerTimeoutError:
            raise GatewayTimeoutError(
                f"OpenAI timeout after {self.timeout}s", provider=self.provider
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
                "OpenAI rate limit exceeded", provider=self.provider, status_code=429
            )
        if response.status >= 400:
            text = await response.text()
            raise GatewayError(
                f"OpenAI error {response.status}: {text}",
                provider=self.provider,
                status_code=response.status,
            )
