from abc import ABC, abstractmethod
import logging
import aiohttp
from typing import Dict, List, Optional, Tuple
from app.schema import LLMProvider, Message, UsageInfo

logger = logging.getLogger(__name__)


def _build_connector(use_proxy: bool, proxy_url: str) -> aiohttp.BaseConnector:
    if use_proxy:
        try:
            from aiohttp_socks import ProxyConnector

            logger.info(f"[PROXY] Creating connector via {proxy_url} (remote DNS)")
            return ProxyConnector.from_url(
                proxy_url,
                rdns=True,
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
            )
        except ImportError:
            logger.error("[PROXY] aiohttp-socks not installed! Run: pip install aiohttp-socks")
            raise

    return aiohttp.TCPConnector(
        limit=100,
        limit_per_host=30,
        ttl_dns_cache=300,
    )


class BaseLLMGateway(ABC):
    provider: LLMProvider
    default_model: str
    MAX_TEMPERATURE: float = 2.0

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout: int = 60,
        use_proxy: bool = False,
        proxy_url: str = "socks5://xray:10808",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
        self.timeout = timeout
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = _build_connector(self.use_proxy, self.proxy_url)
            logger.info(
                f"[{self.provider}] Session: proxy={self.use_proxy}, "
                f"url={self.proxy_url if self.use_proxy else 'direct'}"
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.timeout, connect=15),
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _clamp_temperature(self, temperature: float) -> float:
        clamped = min(temperature, self.MAX_TEMPERATURE)
        if clamped != temperature:
            logger.warning(f"[{self.provider}] Temperature {temperature} clamped to {clamped}")
        return clamped

    def _resolve_model(self, model: Optional[str]) -> str:
        return model or self.default_model

    def _format_messages(self, messages: List[Message]) -> List[Dict]:
        return [{"role": m.role.value, "content": m.content} for m in messages]

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Tuple[str, UsageInfo, str]: ...

    @abstractmethod
    async def health_check(self) -> Tuple[bool, Optional[str]]: ...
