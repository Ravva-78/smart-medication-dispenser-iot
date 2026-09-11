"""
Core Logging Infrastructure.

Purpose:
    Provides centralized logger factory and logging configuration.

Responsibilities:
    - `get_logger(name: str) -> logging.Logger`
    - `configure_logging(level: str)`
"""

import logging
from typing import Optional


def configure_logging(level: str = "INFO") -> None:
    """Configure system-wide root logger format and log level."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger instance for a given module name."""
    return logging.getLogger(name)


__all__ = ["configure_logging", "get_logger"]
