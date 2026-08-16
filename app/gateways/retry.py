import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    retry_if_exception,
)

from app.exceptions import GatewayTimeoutError, GatewayRateLimitError, GatewayError

logger = logging.getLogger(__name__)


def is_retryable_exception(exception):
    if isinstance(exception, (GatewayTimeoutError, GatewayRateLimitError)):
        return True
    if isinstance(exception, GatewayError):
        retryable_codes = {500, 502, 503, 504}
        return exception.status_code in retryable_codes
    return False


def with_retry(max_attempts: int = 3, min_wait: float = 1.0, max_wait: float = 8.0):
    return retry(
        retry=retry_if_exception(is_retryable_exception),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
