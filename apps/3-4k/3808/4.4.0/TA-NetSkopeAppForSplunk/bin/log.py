import ta_netskopeappforsplunk_declare  # noqa: F401

import os
import logging
import logging.handlers

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.clilib import cli_common as cli

DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = (
    "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s "
    "file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s"
)


def get_file_handler(log_file, input_name):
    """Return file handler."""
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, mode="a", maxBytes=25000000, backupCount=10
    )
    if input_name:
        custom_log_format = (
            "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s "
            "file=%(filename)s:%(funcName)s:%(lineno)d | input=\"{}\" | %(message)s"
        ).format(input_name)
        formatter = logging.Formatter(custom_log_format)
    else:
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    file_handler.setFormatter(formatter)
    file_handler.propagate = False
    return file_handler


def get_log_file_name(file_path, prefix="ta_netskopeappforsplunk_"):
    """Generate log file name from path."""
    tmp_file_name = os.path.splitext(os.path.basename(file_path))[0]
    file_name = "{}{}.log".format(prefix, tmp_file_name)
    return file_name


def get_logger(file_path=None, input_type=None):
    """
    Get Logger.

    :param level: log level
    :return: logger object
    """
    logger = logging.getLogger(ta_netskopeappforsplunk_declare.ta_name)
    logger.propagate = False

    cfg = cli.getConfStanza("ta_netskopeappforsplunk_settings", "logging")
    log_level = str(cfg.get("loglevel")).upper()
    log_level = getattr(logging, log_level) if hasattr(logging, log_level) else DEFAULT_LOG_LEVEL
    logger.setLevel(log_level)

    if file_path is None:
        return logger

    file_name = get_log_file_name(file_path)
    log_file = make_splunkhome_path(["var", "log", "splunk", file_name])

    file_handler_exists = any(
        [
            True
            for handler in logger.handlers
            if hasattr(handler, "baseFilename") and handler.baseFilename == log_file
        ]
    )
    if not file_handler_exists:
        file_handler = get_file_handler(log_file, input_type)
        logger.addHandler(file_handler)

    return logger
