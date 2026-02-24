"""
Structured logging configuration.

Architecture Decision:
- JSON logging in production for log aggregation systems (Datadog, ELK, CloudWatch)
- Human-readable text format in development
- Request IDs propagated through log context for distributed tracing
- Separate log levels per component (uvicorn access logs silenced by default)
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone

import structlog
from structlog.types import EventDict, WrappedLogger

from app.core.config import settings


def add_timestamp(
    logger: WrappedLogger, method: str, event_dict: EventDict
) -> EventDict:
    """Add ISO8601 UTC timestamp to every log entry."""
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def add_environment(
    logger: WrappedLogger, method: str, event_dict: EventDict
) -> EventDict:
    """Add environment tag for log routing."""
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def setup_logging() -> None:
    """
    Configure structlog for structured, leveled, context-aware logging.

    Uses stdlib logging as the backend so third-party libraries
    (SQLAlchemy, uvicorn, etc.) integrate seamlessly.
    """
    # Ensure log directory exists
    if settings.LOG_FILE:
        os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)

    # Processors applied to every log entry
    shared_processors = [
        structlog.contextvars.merge_contextvars,  # Thread-local context (request_id etc.)
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_timestamp,
        add_environment,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.LOG_FORMAT == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL)
        ),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    handlers = [console_handler]

    # File handler with rotation (production)
    if settings.LOG_FILE:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            settings.LOG_FILE,
            when="midnight",
            backupCount=30,  # Keep 30 days of logs
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    root_logger.handlers = handlers

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
