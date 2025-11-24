"""Central logging configuration for FlowScribe."""
from __future__ import annotations

import logging
from typing import Optional

try:
    from rich.logging import RichHandler
except Exception:  # pragma: no cover - Rich is optional
    RichHandler = None  # type: ignore


def setup_logging(level: int = logging.INFO, rich: bool = True) -> logging.Logger:
    """Configure and return the application logger.

    Rich is optional; if unavailable, fallback to standard logging handlers.
    """

    handlers = []
    if rich and RichHandler is not None:
        handlers.append(
            RichHandler(
                rich_tracebacks=True,
            )
        )
    else:  # pragma: no cover - depends on optional dependency
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
    )
    logger = logging.getLogger("flowscribe")
    logger.setLevel(level)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Retrieve a child logger beneath the FlowScribe root logger."""

    root = logging.getLogger("flowscribe")
    return root.getChild(name) if name else root
