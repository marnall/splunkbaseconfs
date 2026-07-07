#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import time
import logging
import contextvars
from logging.handlers import RotatingFileHandler

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))


# ---------------------------------------------------------------------------
# Per-request "effective logger" context
# ---------------------------------------------------------------------------
#
# Shared helper functions in trackme_libs*.py historically logged through the
# bare root ``logging`` module (``logging.info(...)``). That worked only while
# every REST handler ran a module-load block that redirected the root logger's
# handlers to its own per-handler RotatingFileHandler. That redirect was a
# process-global mutation: in splunkd's shared process (all handlers loaded
# together) it leaked one handler's logs into another's file, and in a
# custom-command process it overwrote the command's own root logger. PR #1712
# removed it from all 81 handlers, restoring correctness — but it also silenced
# every lib-level trace in the REST-handler request path (the root logger is
# unconfigured there, so INFO/DEBUG lines vanish).
#
# This context var restores those traces WITHOUT touching the root logger.
# RESTHandler.handle() sets it to the handler's own named logger for the
# duration of a request; the lib helpers log through get_effective_logger().
# When it is unset (custom-command process, background threads), the fallback
# is the root logger — exactly the post-#1712 behaviour the command processes
# rely on (e.g. schema-migration traces staying in trackme_tracker_health.log).
#
# Because contextvars are per-execution-context (and a freshly-started thread
# begins with an empty context), there is no cross-handler / cross-request leak
# — the failure mode the removed redirect caused.

_request_logger = contextvars.ContextVar("trackme_request_logger", default=None)


def set_request_logger(logger: logging.Logger):
    """Bind ``logger`` as the effective logger for the current context.

    Returns the ``contextvars.Token`` to pass back to
    :func:`reset_request_logger` (call it in a ``finally`` block).
    """
    return _request_logger.set(logger)


def reset_request_logger(token) -> None:
    """Restore the effective logger to its previous value."""
    try:
        _request_logger.reset(token)
    except (ValueError, LookupError):
        # Token created in a different context (defensive — should not happen
        # given handle() sets and resets in the same context). Never raise from
        # a logging-teardown path.
        pass


def get_effective_logger() -> logging.Logger:
    """Return the logger shared-lib helpers should log through.

    The per-request named handler logger when set (REST request path), else the
    root logger (custom-command process / background threads) — never silently
    nowhere.
    """
    logger = _request_logger.get()
    if logger is not None:
        return logger
    return logging.getLogger()


def setup_logger(
    name: str, logfile: str, level=logging.INFO, redirect_root: bool = False
) -> logging.Logger:
    """
    Set up a dedicated logger.

    :param name: Unique name for the logger (e.g. 'myapp.rest.config')
    :param logfile: Name of the log file (relative to $SPLUNK_HOME/var/log/splunk)
    :param level: Logging level, defaults to logging.INFO
    :param redirect_root: If True, attach the same handler to the root logger (not recommended for shared apps)
    :return: Configured logger instance
    """

    splunkhome = os.environ.get("SPLUNK_HOME", "/opt/splunk")
    log_path = os.path.join(splunkhome, "var", "log", "splunk", logfile)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Prevent bubbling

    # Check if this handler is already attached
    if not any(
        isinstance(h, RotatingFileHandler)
        and getattr(h, "baseFilename", None) == log_path
        for h in logger.handlers
    ):
        handler = RotatingFileHandler(
            log_path, mode="a", maxBytes=10 * 1024 * 1024, backupCount=1
        )
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(filename)s %(funcName)s %(lineno)d %(message)s"
        )
        logging.Formatter.converter = time.gmtime
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Optional: redirect root logger
        if redirect_root:
            root_logger = logging.getLogger()
            root_logger.setLevel(level)
            root_logger.propagate = False
            if not any(
                isinstance(h, RotatingFileHandler)
                and getattr(h, "baseFilename", None) == log_path
                for h in root_logger.handlers
            ):
                root_logger.addHandler(handler)

    return logger
