import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers.llm import router as llm_router
from app.dependencies import get_llm_router
from app.db.database import engine
from app.redis_client import get_redis_pool
from app.settings import settings

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    router = get_llm_router()
    redis_client = get_redis_pool()
    await redis_client.ping()
    logger.info(f"[STARTUP] AI Gateway ready | providers: {router.get_available_providers()}")
    yield

    for gateway in router._gateways.values():
        await gateway.close()

    await redis_client.aclose()
    await engine.dispose()
    logger.info("[SHUTDOWN] AI Gateway stopped")


app = FastAPI(
    title="AI Gateway",
    description="API-шлюз с проверкой API-ключа (PostgreSQL) и rate limiting (Redis)",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(llm_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"service": "ai-gateway", "docs": "/docs"}
