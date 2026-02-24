"""
Request ID middleware.
Injects a unique ID into each request for distributed tracing.
The ID is propagated through logs and returned in response headers.
"""

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Honor incoming request ID (from client or upstream service)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store in request state for access in route handlers
        request.state.request_id = request_id

        # Bind to structlog context — all log lines in this request include it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
