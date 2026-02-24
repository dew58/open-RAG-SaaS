"""
Centralized exception definitions and handlers.

Architecture Decision:
- AppException base class with HTTP status code and error code
- Error codes are machine-readable strings (e.g., "AUTH_001") for client handling
- All unhandled exceptions are caught and sanitized before response
- Stack traces never leaked to clients in production
"""

import logging
from typing import Any, Dict, Optional

import structlog
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class AppException(Exception):
    """
    Base application exception.
    Raised in service/repository layer, caught by FastAPI handler.
    """
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "APP_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_001",
        )


class AuthorizationError(AppException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTH_002",
        )


class NotFoundError(AppException):
    def __init__(self, resource: str, resource_id: Any = None):
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} '{resource_id}' not found"
        super().__init__(
            message=msg,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
        )


class ConflictError(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
        )


class FileSizeError(AppException):
    def __init__(self, max_mb: int):
        super().__init__(
            message=f"File exceeds maximum size of {max_mb}MB",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_code="FILE_SIZE",
        )


class FileTypeError(AppException):
    def __init__(self, allowed: list):
        super().__init__(
            message=f"File type not allowed. Accepted: {', '.join(allowed)}",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error_code="FILE_TYPE",
        )


class RagPipelineError(AppException):
    def __init__(self, message: str = "RAG pipeline error"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="RAG_ERROR",
        )


class RateLimitError(AppException):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT",
            details={"retry_after": retry_after},
        )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle known application exceptions with structured response."""
    logger.warning(
        "Application exception",
        error_code=exc.error_code,
        message=exc.message,
        path=str(request.url),
        method=request.method,
        status_code=exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with field-level detail."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(
        "Validation error",
        path=str(request.url),
        errors=errors,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"errors": errors},
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for unhandled exceptions.
    Logs full stack trace but returns sanitized message to client.
    """
    logger.error(
        "Unhandled exception",
        path=str(request.url),
        method=request.method,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An internal error occurred. Please try again later.",
            "details": {},
        },
    )
