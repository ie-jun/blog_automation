"""Loguru-based logger factory for blog_automation.

Usage:
    from core.logger import setup_logger
    logger = setup_logger("neighbor")
"""

import sys
from pathlib import Path

from loguru import logger as _base_logger

from config import LOGS_DIR

# Track whether the shared stderr handler has been registered.
_stderr_added: bool = False

# Map module_name -> file handler ID so we can replace it on repeated calls.
_file_handler_ids: dict[str, int] = {}


def setup_logger(module_name: str) -> "_base_logger.__class__":
    """Create a module-specific logger with date-based log rotation.

    Each module gets its own rotating file handler while sharing one stderr
    handler.  Calling this function multiple times for the same module_name
    safely replaces only that module's file handler — other modules' handlers
    are left untouched.

    Args:
        module_name: Short name used as log file prefix (e.g. "neighbor", "draft").

    Returns:
        Configured loguru Logger instance bound to the given module.
    """
    global _stderr_added

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Register the shared stderr handler exactly once across all modules.
    if not _stderr_added:
        try:
            _base_logger.remove(0)  # Remove loguru's built-in default handler
        except ValueError:
            pass
        _base_logger.add(
            sys.stderr,
            level="INFO",
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
            ),
        )
        _stderr_added = True

    # Replace this module's file handler if it was previously registered.
    if module_name in _file_handler_ids:
        try:
            _base_logger.remove(_file_handler_ids[module_name])
        except ValueError:
            pass

    log_path = LOGS_DIR / f"{module_name}_{{time:YYYYMMDD}}.log"
    handler_id = _base_logger.add(
        str(log_path),
        level="DEBUG",
        rotation="00:00",       # rotate at midnight
        retention="30 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
    )
    _file_handler_ids[module_name] = handler_id

    return _base_logger.bind(module=module_name)
