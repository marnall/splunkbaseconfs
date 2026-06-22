"""Shared logging configuration for Whisper Security TA.

Provides centralized logging setup with Splunk-compatible log format,
RotatingFileHandler writing to $SPLUNK_HOME/var/log/splunk/, and
logger names following the splunk.whisper.<component> convention.

Entry points (search commands, modular inputs, alert actions, REST handlers)
call ``setup_logging()`` once at startup. Library modules call ``get_logger()``
to obtain a correctly-named child logger that inherits the handler configuration.

References:
    - Splunk Logging Extensions: https://dev.splunk.com/enterprise/docs/developapps/addsupport/logging/loggingsplunkextensions
    - Logging Best Practices: https://dev.splunk.com/enterprise/docs/developapps/addsupport/logging/loggingbestpractices
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import time

# Root logger name for all Whisper TA modules
LOGGER_ROOT = "splunk.whisper"

# Log file name (single shared log for the TA)
LOG_FILENAME = "ta_whisper_security.log"

# Splunk-recommended log format with timestamps, level, module, function, and line
# Uses UTC timestamps with timezone for consistency across environments
LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(funcName)s:%(lineno)d - %(message)s"

# RotatingFileHandler defaults
MAX_LOG_BYTES = 10_000_000  # 10 MB
BACKUP_COUNT = 5

# Default log level
DEFAULT_LOG_LEVEL = logging.INFO


def get_logger(component: str) -> logging.Logger:
    """Get a logger following the splunk.whisper.<component> naming convention.

    This should be used by ALL modules instead of ``logging.getLogger(__name__)``.
    The returned logger inherits handler configuration from the root
    ``splunk.whisper`` logger set up by ``setup_logging()``.

    Args:
        component: The component name (e.g., 'api_client', 'health_input').

    Returns:
        Logger instance named ``splunk.whisper.<component>``.
    """
    return logging.getLogger(f"{LOGGER_ROOT}.{component}")


def setup_logging(component: str = "ta", log_level: int = DEFAULT_LOG_LEVEL) -> logging.Logger:
    """Configure logging for a Whisper TA entry point.

    Sets up a RotatingFileHandler writing to
    ``$SPLUNK_HOME/var/log/splunk/ta_whisper_security.log`` with the
    Splunk-recommended format. Should be called once at startup from each
    entry point (search commands, modular inputs, alert actions, REST handlers).

    Library/helper modules should NOT call this -- they inherit the logging
    configuration from the entry point via the ``splunk.whisper`` logger hierarchy.

    Args:
        component: The component name for the logger.
        log_level: Logging level (default: INFO).

    Returns:
        Configured logger instance.
    """
    logger = get_logger(component)

    # Avoid adding duplicate handlers if called multiple times
    root_logger = logging.getLogger(LOGGER_ROOT)
    if root_logger.handlers:
        logger.setLevel(log_level)
        return logger

    # Set up the root whisper logger with handler
    root_logger.setLevel(log_level)

    # Create RotatingFileHandler if SPLUNK_HOME is available
    splunk_home = os.environ.get("SPLUNK_HOME", "")
    log_dir = os.path.join(splunk_home, "var", "log", "splunk") if splunk_home else ""

    if log_dir and os.path.isdir(log_dir):
        log_path = os.path.join(log_dir, LOG_FILENAME)
        handler = logging.handlers.RotatingFileHandler(
            log_path,
            mode="a",
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
        )
        formatter = logging.Formatter(LOGGING_FORMAT)
        formatter.converter = time.gmtime  # UTC timestamps
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Also add a StreamHandler for stderr (splunkd captures stderr)
    stream_handler = logging.StreamHandler()
    stream_formatter = logging.Formatter(LOGGING_FORMAT)
    stream_formatter.converter = time.gmtime
    stream_handler.setFormatter(stream_formatter)
    root_logger.addHandler(stream_handler)

    logger.setLevel(log_level)
    return logger
