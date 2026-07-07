"""Log Manager for Cisco App for Nexus 9k."""

import logging
import logging.handlers
import os

from splunk.clilib import cli_common as cli
from splunk.clilib.bundle_paths import make_splunkhome_path

APP_NAME = __file__.split(os.sep)[-3]
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = (
    "%(asctime)s log_level=%(levelname)s pid=%(process)d tid=%(threadName)s "
    "file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s"
)
LOG_LEVEL_MAPPING = {
    'CRITICAL': "CRITICAL",
    'ERROR': "ERROR",
    'WARN': "WARNING",
    'WARNING': "WARNING",
    'INFO': "INFO",
    'DEBUG': "DEBUG",
}


def get_file_handler(log_file):
    """Return file handler."""
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, mode="a", maxBytes=25000000, backupCount=10
    )
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    file_handler.setFormatter(formatter)
    file_handler.propagate = False
    return file_handler


def get_log_file_name(file_path, prefix="TA_cisco-Nexus-9k_"):
    """Generate log file name from path."""
    tmp_file_name = os.path.splitext(os.path.basename(file_path))[0]
    file_name = "{}{}.log".format(prefix, tmp_file_name)
    return file_name


def get_logger(file_path=None):
    """
    Get Logger.

    :param level: log level
    :return: logger object
    """
    logger = logging.getLogger(file_path)
    logger.propagate = False

    try:
        cfg = cli.getAppConf("cisco_nexus_setup", "TA_cisco-Nexus-9k")
        log_level = str(cfg.get("logging", {}).get("loglevel")).upper()
    except Exception:
        log_level = DEFAULT_LOG_LEVEL

    if log_level.upper() not in LOG_LEVEL_MAPPING:
        log_level = DEFAULT_LOG_LEVEL

    logger.setLevel(LOG_LEVEL_MAPPING.get(log_level.upper()))

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
        file_handler = get_file_handler(log_file)
        logger.addHandler(file_handler)

    return logger
