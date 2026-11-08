"""Конфігурація структурованого логування у форматі JSON (structlog)."""

import logging
import sys

import structlog


def setup_logging() -> None:
    """Налаштування JSON-форматування логів."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Перенаправлення стандартного logging у structlog
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
