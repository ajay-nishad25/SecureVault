"""Tests for safe logging infrastructure and secret redaction."""

import logging
from app.core.logging import SafeLogFilter, get_logger, setup_logging


def test_get_logger_namespacing() -> None:
    """Verify that get_logger returns loggers properly namespaced under 'securevault'."""
    logger = get_logger("test_module")
    assert logger.name == "securevault.test_module"

    root_named = get_logger("securevault")
    assert root_named.name == "securevault"


def test_safe_log_filter_redacts_sensitive_patterns() -> None:
    """Verify that SafeLogFilter redacts accidental inclusions of secrets in log messages."""
    log_filter = SafeLogFilter()

    # Record simulating accidental password logging
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Authentication failed for user user@example.com with password: mySecretPassword123",
        args=(),
        exc_info=None,
    )
    result = log_filter.filter(record)
    assert result is True
    assert "mySecretPassword123" not in record.msg
    assert "password: [REDACTED]" in record.msg


def test_safe_log_filter_preserves_safe_messages() -> None:
    """Verify that normal operational log messages are unaltered by the filter."""
    log_filter = SafeLogFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Application started successfully in data directory C:\\SecureVault",
        args=(),
        exc_info=None,
    )
    result = log_filter.filter(record)
    assert result is True
    assert record.msg == "Application started successfully in data directory C:\\SecureVault"
