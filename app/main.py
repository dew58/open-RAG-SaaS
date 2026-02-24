"""
Main FastAPI application entry point.

Architecture Decision:
- Lifespan context manager for startup/shutdown (FastAPI 0.95+ pattern)
- Centralized middleware registration order matters: outermost = last executed
- Router prefix versioning (/api/v1) for future API evolution
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging_config import setup_logging
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.routers import auth, clients, documents, chat, export
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from fastapi.exceptions import RequestValidationError

# Initialize structured logging before anything else
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    Creates DB tables on startup (Alembic handles migrations in production).
    Cleans up resources on shutdown.
    """
    logger.info("Starting RAG SaaS application", extra={"env": settings.ENVIRONMENT})

    # In production, tables are managed by Alembic migrations.
    # This is a safety net for development/first-run.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables verified/created")
    yield

    # Cleanup: dispose connection pool on shutdown
    await engine.dispose()
    logger.info("Application shutdown complete")


def create_application() -> FastAPI:
    """
    Application factory pattern.
    Separating creation from running enables easier testing.
    """
    app = FastAPI(
        title="Multi-Tenant RAG SaaS API",
        description="Production-grade Retrieval-Augmented Generation platform",
        version="1.0.0",
        docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # ── Middleware (registered in reverse execution order) ──────────────────
    # GZip: compress responses > 1KB — reduces bandwidth significantly
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS: strict in production, permissive in dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    )

    # Rate limiting: Redis-backed in production, in-memory for dev
    app.add_middleware(RateLimitMiddleware)

    # Request ID: trace requests across services and logs
    app.add_middleware(RequestIDMiddleware)

    # ── Exception Handlers ──────────────────────────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # ── Routers ─────────────────────────────────────────────────────────────
    API_PREFIX = "/api/v1"
    app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["Authentication"])
    app.include_router(clients.router, prefix=f"{API_PREFIX}/clients", tags=["Clients"])
    app.include_router(documents.router, prefix=f"{API_PREFIX}/documents", tags=["Documents"])
    app.include_router(chat.router, prefix=f"{API_PREFIX}/chat", tags=["Chat"])
    app.include_router(export.router, prefix=f"{API_PREFIX}/export", tags=["Export"])

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Kubernetes liveness probe endpoint."""
        return JSONResponse({"status": "healthy", "version": "1.0.0"})

    return app


app = create_application()
