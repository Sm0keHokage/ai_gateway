import logging
from functools import lru_cache

from app.router import LLMRouter
from app.gateways.openai_gateway import OpenAIGateway
from app.gateways.anthropic_gateway import AnthropicGateway
from app.gateways.gemini_gateway import GeminiGateway
from app.schema import LLMProvider
from app.settings import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_llm_router() -> LLMRouter:
    gateways = {}

    use_proxy = settings.PROXY.ENABLED
    proxy_url = settings.PROXY.URL
    logger.info(f"[INIT] Proxy: enabled={use_proxy}, url={proxy_url if use_proxy else '-'}")

    if settings.OPENAI.API_KEY:
        gateways[LLMProvider.OPENAI] = OpenAIGateway(
            api_key=settings.OPENAI.API_KEY.get_secret_value(),
            base_url=settings.OPENAI.BASE_URL,
            default_model=settings.OPENAI.DEFAULT_MODEL,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
            use_proxy=use_proxy,
            proxy_url=proxy_url,
        )

    if settings.ANTHROPIC.API_KEY:
        gateways[LLMProvider.ANTHROPIC] = AnthropicGateway(
            api_key=settings.ANTHROPIC.API_KEY.get_secret_value(),
            base_url=settings.ANTHROPIC.BASE_URL,
            default_model=settings.ANTHROPIC.DEFAULT_MODEL,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
            use_proxy=use_proxy,
            proxy_url=proxy_url,
        )

    if settings.GEMINI.API_KEY:
        gateways[LLMProvider.GEMINI] = GeminiGateway(
            api_key=settings.GEMINI.API_KEY.get_secret_value(),
            base_url=settings.GEMINI.BASE_URL,
            default_model=settings.GEMINI.DEFAULT_MODEL,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
            use_proxy=use_proxy,
            proxy_url=proxy_url,
        )

    if not gateways:
        raise RuntimeError("No LLM providers configured in .env!")

    return LLMRouter(gateways)
