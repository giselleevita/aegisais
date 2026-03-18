import logging
import logging.config
import os
import sys
import structlog

def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # 1. Standard library logging setup
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
    )

    # 2. Structlog configuration
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            # Output as JSON in production/docker, pretty-print in dev
            structlog.processors.JSONRenderer() if os.getenv("APP_ENV") == "docker" else structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Auto-configure on import
configure_logging()
logger = structlog.get_logger("aegisais")
