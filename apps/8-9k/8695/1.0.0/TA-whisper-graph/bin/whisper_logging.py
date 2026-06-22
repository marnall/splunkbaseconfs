"""Shared logging configuration for Whisper Security TA.

Provides centralized logging setup with Splunk-compatible log format,
RotatingFileHandler writing to
``$SPLUNK_HOME/var/log/splunk/TA-whisper-graph/`` (app-namespaced path
for Cloud Victoria compliance; falls back to the shared
``$SPLUNK_HOME/var/log/splunk/`` dir if the namespaced subdirectory cannot be
created), and logger names following the ``splunk.whisper.<component>`` convention.

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

# App name used to namespace the log directory under
# $SPLUNK_HOME/var/log/splunk/<APP_NAME>/. Splunk Cloud Victoria Experience
# requires app-namespaced log paths -- writing to the shared
# $SPLUNK_HOME/var/log/splunk/ root may be sandboxed or rejected by DCS.
# See Issue #492.
APP_NAME = "TA-whisper-graph"

# Log file name (single shared log for the TA)
LOG_FILENAME = "ta_whisper_graph.log"

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
        component: The component name (e.g., 'api_client', 'baseline_input').

    Returns:
        Logger instance named ``splunk.whisper.<component>``.
    """
    return logging.getLogger(f"{LOGGER_ROOT}.{component}")


def setup_logging(component: str = "ta", log_level: int = DEFAULT_LOG_LEVEL) -> logging.Logger:
    """Configure logging for a Whisper TA entry point.

    Sets up a RotatingFileHandler writing to the app-namespaced log directory:

        $SPLUNK_HOME/var/log/splunk/TA-whisper-graph/ta_whisper_graph.log

    The app-namespaced path is required for Splunk Cloud Victoria Experience
    (DCS sandboxing). If the namespaced subdirectory cannot be created, falls
    back to the shared ``$SPLUNK_HOME/var/log/splunk/`` directory for
    backward compatibility on Splunk Enterprise and Cloud Classic.

    Should be called once at startup from each entry point (search commands,
    modular inputs, alert actions, REST handlers).

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

    # Create RotatingFileHandler if SPLUNK_HOME is available.
    #
    # Log directory selection (Issue #492):
    #   1. Preferred: $SPLUNK_HOME/var/log/splunk/<APP_NAME>/  (Cloud Victoria
    #      app-namespaced path -- DCS allows writes here without sandboxing).
    #   2. Fallback: $SPLUNK_HOME/var/log/splunk/  (shared dir -- works on
    #      Enterprise and Cloud Classic but may be sandboxed on Victoria).
    #
    # We try to create the namespaced directory first; if creation fails
    # (e.g. read-only filesystem in tests, or unexpected permission error),
    # we fall back to the shared dir so logging still works.
    splunk_home = os.environ.get("SPLUNK_HOME", "")
    shared_log_dir = os.path.join(splunk_home, "var", "log", "splunk") if splunk_home else ""

    log_dir = ""
    if shared_log_dir and os.path.isdir(shared_log_dir):
        namespaced_log_dir = os.path.join(shared_log_dir, APP_NAME)
        try:
            os.makedirs(namespaced_log_dir, exist_ok=True)
            log_dir = namespaced_log_dir
        except OSError:
            # Fall back to the shared dir for backward compatibility on
            # Enterprise / Cloud Classic where this has always worked.
            log_dir = shared_log_dir

    if log_dir:
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
