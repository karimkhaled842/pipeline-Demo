"""Structured JSON logging with structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from src.app.core.config import get_settings


def add_app_context(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Inject application-level context into every log record."""
    settings = get_settings()
    event_dict["app"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["environment"] = settings.environment
    return event_dict


def configure_logging() -> None:
    """Bootstrap structlog for the application."""
    settings = get_settings()

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
    ]

    if settings.is_production or not settings.debug:
        # JSON output for production / CI
        processors: list[Processor] = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Pretty console output for local development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging so third-party libs integrate
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str | None = None) -> Any:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
