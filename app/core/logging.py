from __future__ import annotations

import logging
from logging.config import dictConfig

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    log_level = settings.log_level.upper()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": log_level,
                }
            },
            "root": {
                "handlers": ["console"],
                "level": log_level,
            },
            "loggers": {
                "uvicorn.error": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False,
                },
                "sqlalchemy.engine": {
                    "level": "INFO" if settings.log_sql_queries else "WARNING",
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
        }
    )
    logging.getLogger(__name__).info("Logging configured at %s level.", log_level)
