import logging
import sys
from typing import Any, Dict


def configure_logging() -> None:
    """
    Configure application-wide structured logging.

    This uses a simple JSON-like line format suitable for aggregation
    in tools such as ELK, Loki, or Stackdriver.
    """

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Dict[str, Any],
) -> None:
    """
    Helper to emit log messages with structured context as a flat dict.
    """

    if context:
        message = f"{message} | context={context!r}"
    logger.log(level, message)

