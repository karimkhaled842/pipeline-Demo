"""FastAPI application factory and lifecycle management."""

import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram

from src.app.api.v1 import auth, health, items, users
from src.app.core.config import get_settings
from src.app.core.logging import configure_logging, get_logger
from src.app.db.session import create_tables

configure_logging()
logger = get_logger(__name__)

# ── Prometheus metrics ────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown logic."""
    settings = get_settings()
    logger.info("app_starting", environment=settings.environment, version=settings.app_version)

    # Auto-create tables in non-production environments
    if not settings.is_production:
        await create_tables()

    logger.info("app_ready")
    yield

    logger.info("app_shutting_down")


# ── Factory ───────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="SecureApp",
        description=(
            "A production-ready FastAPI application demonstrating DevSecOps best practices:\n"
            "- JWT authentication with bcrypt passwords\n"
            "- PostgreSQL persistence via async SQLAlchemy\n"
            "- Redis caching layer\n"
            "- Prometheus metrics & structured JSON logging\n"
            "- Kubernetes-ready health, liveness, and readiness probes"
        ),
        version=settings.app_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
    )

    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # Tighten per deployment
        )

    # ── Request timing / metrics middleware ───────────────────────────────────
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        latency = time.monotonic() - start
        endpoint = request.url.path
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(latency)
        response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "")
        response.headers["X-Process-Time"] = f"{latency:.4f}"
        return response

    # ── Security headers ──────────────────────────────────────────────────────
    @app.middleware("http")
    async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        return response

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            path=str(request.url),
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(items.router, prefix="/api/v1")

    # Root redirect
    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"message": "SecureApp API", "docs": "/docs", "health": "/api/v1/health"}

    return app


app = create_app()
