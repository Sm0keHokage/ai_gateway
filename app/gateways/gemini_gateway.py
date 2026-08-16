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


class GeminiGateway(BaseLLMGateway):
    provider = LLMProvider.GEMINI
    MAX_TEMPERATURE = 2.0

    def _to_gemini_format(self, messages: List[Message]) -> Tuple[Optional[str], List[Dict]]:
        system_instruction = None
        contents = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_instruction = msg.content
            elif msg.role == MessageRole.USER:
                contents.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == MessageRole.ASSISTANT:
                contents.append({"role": "model", "parts": [{"text": msg.content}]})
        return system_instruction, contents

    def _build_payload(self, messages: List[Message], temperature: float) -> Dict:
        system_instruction, contents = self._to_gemini_format(messages)
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system_instruction:
            payload["system_instruction"] = {"parts": [{"text": system_instruction}]}
        return payload

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
        payload = self._build_payload(messages, safe_temp)

        url = f"{self.base_url}/models/{resolved_model}:generateContent?key={self.api_key}"

        try:
            session = await self.get_session()
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                await self._raise_for_status(response)
                data = await response.json()

            content = data["candidates"][0]["content"]["parts"][0]["text"]
            raw_usage = data.get("usageMetadata", {})
            usage = UsageInfo(
                prompt_tokens=raw_usage.get("promptTokenCount", 0),
                completion_tokens=raw_usage.get("candidatesTokenCount", 0),
                total_tokens=raw_usage.get("totalTokenCount", 0),
            )
            return content, usage, resolved_model

        except aiohttp.ServerTimeoutError:
            raise GatewayTimeoutError(
                f"Gemini timeout after {self.timeout}s", provider=self.provider
            )

    async def health_check(self) -> Tuple[bool, Optional[str]]:
        try:
            session = await self.get_session()
            async with session.get(
                f"{self.base_url}/models?key={self.api_key}",
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
                "Gemini rate limit exceeded", provider=self.provider, status_code=429
            )
        if response.status >= 400:
            text = await response.text()
            raise GatewayError(
                f"Gemini error {response.status}: {text}",
                provider=self.provider,
                status_code=response.status,
            )
