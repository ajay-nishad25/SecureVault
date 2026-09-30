"""SecureVault — Safe Logging Infrastructure.

Defines safe application logging policies and helpers.

LOGGING POLICY:
Logging is strictly restricted to operational lifecycle events (startup,
shutdown, file read/write status, error summaries).
The logging pipeline must NEVER record:
  - Master passwords
  - Cryptographic keys (KEK, DEK, raw bytes)
  - Decrypted vault payloads, usernames, or passwords
  - System clipboard contents
  - Authentication tokens or salts
"""

from __future__ import annotations

import logging
import re
from typing import Any

# Patterns that indicate accidental sensitive data leakage in log strings
SENSITIVE_PATTERNS = [
    re.compile(r"(password\s*[:=]\s*)[^\s,]+", re.IGNORECASE),
    re.compile(r"(secret\s*[:=]\s*)[^\s,]+", re.IGNORECASE),
    re.compile(r"(token\s*[:=]\s*)[^\s,]+", re.IGNORECASE),
    re.compile(r"(key\s*[:=]\s*)[^\s,]+", re.IGNORECASE),
]

_LOGGER_INITIALIZED: bool = False


class SafeLogFilter(logging.Filter):
    """Logging filter that redacts accidental secret leaks in message strings."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern in SENSITIVE_PATTERNS:
                record.msg = pattern.sub(r"\1[REDACTED]", record.msg)
        return True


def setup_logging(level: str = "INFO") -> None:
    """Configure the root application logger with safe formatters and redaction filters."""
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return

    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger("securevault")
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if reconfigured
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SafeLogFilter())
        root_logger.addHandler(handler)

    _LOGGER_INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """Obtain a namespaced child logger under 'securevault'.

    Usage:
        logger = get_logger(__name__)
    """
    if not _LOGGER_INITIALIZED:
        setup_logging()

    if name.startswith("securevault.") or name == "securevault":
        return logging.getLogger(name)
    return logging.getLogger(f"securevault.{name}")
