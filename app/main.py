from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import TabiException
from app.database.session import close_redis, engine, get_redis
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "sqlalchemy.engine": {"level": "WARNING"},
        "uvicorn.access": {"handlers": [], "propagate": False},
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)
    # Warm up Redis connection
    redis = get_redis()
    try:
        await redis.ping()
        logger.info("Redis connection established")
    except Exception as exc:
        logger.warning("Redis not available: %s — rate limiting disabled", exc)

    yield

    logger.info("Shutting down...")
    await close_redis()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# ── Middleware (order matters — outermost added last) ──────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Exception handlers ─────────────────────────────────────────────────────────
@app.exception_handler(TabiException)
async def tabi_exception_handler(request: Request, exc: TabiException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.message, "code": exc.code},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": str(detail), "code": "HTTP_ERROR"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "code": "INTERNAL_ERROR"},
    )


# ── Root (useful for Vercel deployment checks) ────────────────────────────────
@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "success": True,
        "data": {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "health": "/api/v1/health",
            "docs": "/docs" if settings.ENVIRONMENT != "production" else None,
        },
        "message": "Tabi Formulario API",
    }


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["Health"])
async def health_check() -> dict:
    redis_ok = False
    try:
        redis = get_redis()
        await redis.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "redis": "ok" if redis_ok else "unavailable",
        },
        "message": "Service is running",
    }
