from typing import List, Tuple
from app.schema import LLMProvider


class LLMGatewayError(Exception):
    pass


class GatewayError(LLMGatewayError):
    def __init__(self, message: str, provider: LLMProvider = None, status_code: int = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)


class GatewayTimeoutError(GatewayError):
    pass


class GatewayRateLimitError(GatewayError):
    pass


class AllGatewaysFailedError(LLMGatewayError):
    def __init__(self, errors: List[Tuple[LLMProvider, str]]):
        self.errors = errors
        details = "; ".join(f"{provider}: {error}" for provider, error in errors)
        super().__init__(f"All providers failed: {details}")


class ProviderNotConfiguredError(LLMGatewayError):
    pass
