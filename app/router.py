import time
import logging
from typing import Dict, List
from app.gateways.base import BaseLLMGateway
from app.schema import LLMProvider, LLMRequest, LLMResponse, Priority
from app.exceptions import (
    AllGatewaysFailedError,
    ProviderNotConfiguredError,
)

logger = logging.getLogger(__name__)

PRIORITY_ORDERS: Dict[Priority, List[LLMProvider]] = {
    Priority.QUALITY: [LLMProvider.ANTHROPIC, LLMProvider.OPENAI, LLMProvider.GEMINI],
    Priority.COST: [LLMProvider.GEMINI, LLMProvider.OPENAI, LLMProvider.ANTHROPIC],
    Priority.BALANCED: [LLMProvider.OPENAI, LLMProvider.GEMINI, LLMProvider.ANTHROPIC],
}


class LLMRouter:
    def __init__(self, gateways: Dict[LLMProvider, BaseLLMGateway]):
        self._gateways = gateways
        logger.info(f"[LLM ROUTER] Initialized with providers: {list(gateways.keys())}")

    def get_available_providers(self) -> List[LLMProvider]:
        return list(self._gateways.keys())

    def _get_order(self, request: LLMRequest) -> List[LLMProvider]:
        if request.provider != LLMProvider.AUTO:
            return [request.provider]
        return [
            p
            for p in PRIORITY_ORDERS.get(request.priority, PRIORITY_ORDERS[Priority.BALANCED])
            if p in self._gateways
        ]

    async def route(self, request: LLMRequest) -> LLMResponse:
        order = self._get_order(request)
        if not order:
            raise ProviderNotConfiguredError(f"Provider {request.provider} is not configured")

        errors = []
        for provider in order:
            gateway = self._gateways.get(provider)
            if gateway is None:
                errors.append((provider, "not configured"))
                if request.provider != LLMProvider.AUTO:
                    raise ProviderNotConfiguredError(
                        f"Provider {request.provider} is not configured"
                    )
                continue
            try:
                start = time.monotonic()
                logger.info(
                    f"[LLM ROUTER] Trying {provider} | "
                    f"model={request.model or gateway.default_model}"
                )
                content, usage, model_used = await gateway.complete(
                    messages=request.messages,
                    model=request.model,
                    temperature=request.temperature,
                )
                latency = int((time.monotonic() - start) * 1000)
                logger.info(
                    f"[LLM ROUTER] Success {provider} | "
                    f"latency={latency}ms | tokens={usage.total_tokens}"
                )
                return LLMResponse(
                    content=content,
                    provider=provider,
                    model=model_used,
                    usage=usage,
                    latency_ms=latency,
                )
            except Exception as e:
                logger.warning(f"[LLM ROUTER] {provider} failed: {type(e).__name__}: {e}")
                errors.append((provider, str(e)))
                if request.provider != LLMProvider.AUTO:
                    raise

        raise AllGatewaysFailedError(errors)
