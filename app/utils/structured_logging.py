# app/utils/structured_logging.py
"""
Structured logging configuration for MAi-RAG.
Outputs JSON logs in production, colored console logs in development.
"""
import logging
import sys

import structlog


def setup_logging(log_level: str = "INFO"):
    """Configure structlog with appropriate processors."""

    # Shared processors for all environments
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.UnicodeDecoder(),
    ]

    # Check if running in production (no TTY) or development
    if sys.stderr.isatty():
        # Development: colored, human-readable output
        renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            pad_event=35,
        )
    else:
        # Production: JSON output for log aggregation
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to work with structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Suppress noisy third-party loggers
    for noisy in [
        "httpx",
        "httpcore",
        "urllib3",
        "huggingface_hub",
        "sentence_transformers",
    ]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return structlog.get_logger("mai_rag")
