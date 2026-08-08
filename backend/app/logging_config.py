"""structlog setup, shared by the API process and (later) the Celery worker.

Kept free of FastAPI/Celery imports so both processes can call
configure_logging() the same way.
"""

import logging
import sys

import structlog

from app.config import settings


def configure_logging() -> None:
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        # Renders exc_info (set by log.exception()/log.warning(exc_info=True))
        # into a plain "exception" string field. Without this, JSONRenderer
        # would serialize exc_info as a bare `true` and the traceback would
        # never make it into the log line.
        structlog.processors.format_exc_info,
    ]

    if settings.environment == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Formatter applied to plain stdlib `logging` records (uvicorn, SQLAlchemy,
    # etc.) so they render identically to structlog's own log lines.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

    # These loggers already propagate to root; drop their own handlers so
    # lines aren't emitted (and formatted) twice.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(logger_name).handlers = []
        logging.getLogger(logger_name).propagate = True
