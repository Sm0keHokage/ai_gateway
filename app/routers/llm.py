import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.schema import LLMRequest, LLMResponse, HealthResponse, ProviderHealth
from app.router import LLMRouter
from app.dependencies import get_llm_router
from app.rate_limiter import rate_limit
from app.db.models import ApiKey
from app.db.database import get_session_maker
from app.db.repositories import RequestLogRepository
from app.exceptions import (
    AllGatewaysFailedError,
    GatewayError,
    ProviderNotConfiguredError,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["LLM"])


@router.post("/complete", response_model=LLMResponse)
async def complete(
    request: LLMRequest,
    llm_router: LLMRouter = Depends(get_llm_router),
    api_key: ApiKey = Depends(rate_limit),
    session_maker: async_sessionmaker = Depends(get_session_maker),
):
    status_code = 200
    error_message = None
    response: LLMResponse | None = None

    try:
        response = await llm_router.route(request)
    except ProviderNotConfiguredError as e:
        status_code = 400
        error_message = str(e)
        raise HTTPException(400, str(e))
    except GatewayError as e:
        status_code = 502
        error_message = str(e)
        raise HTTPException(502, str(e))
    except AllGatewaysFailedError as e:
        status_code = 503
        error_message = str(e)
        raise HTTPException(503, str(e))
    finally:
        async with session_maker() as log_session:
            async with log_session.begin():
                await RequestLogRepository.create(
                    log_session,
                    {
                        "api_key_id": api_key.id,
                        "provider": (response.provider if response else request.provider),
                        "model": response.model if response else request.model,
                        "status_code": status_code,
                        "latency_ms": response.latency_ms if response else 0,
                        "success": status_code == 200,
                        "error": error_message,
                    },
                )

    return response


@router.get("/health", response_model=HealthResponse)
async def health_check(
    llm_router: LLMRouter = Depends(get_llm_router),
):
    providers = {}
    for provider, gateway in llm_router._gateways.items():
        available, error = await gateway.health_check()
        providers[provider] = ProviderHealth(
            available=available,
            model=gateway.default_model,
            error=error,
        )

    all_ok = all(p.available for p in providers.values())
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        providers=providers,
    )
