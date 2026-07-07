"""this file is for logging module."""
# Standard library imports
import os
import logging
import logging.handlers

# Splunk imports
from splunk.clilib import cli_common as cli
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

DEFAULT_LOG_LEVEL = logging.INFO


def setup_logging(log_name):
    """
    Get a logger object with specified log level.

    :param log_name: (str): name for logger
    :return: logger object
    """
    # Make path till log file
    log_file = make_splunkhome_path(["var", "log", "splunk", "%s.log" % log_name])
    # Get directory in which log file is present
    log_dir = os.path.dirname(log_file)
    # Create directory at the required path to store log file, if not found
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Read log level from conf file
    cfg = cli.getConfStanza("ta_armis_settings", "logging")
    log_level = cfg.get("loglevel")

    logger = logging.getLogger(log_name)
    logger.propagate = False

    # Set log level
    try:
        logger.setLevel(log_level)
    except Exception:
        logger.setLevel(DEFAULT_LOG_LEVEL)

    handler_exists = any([True for h in logger.handlers if h.baseFilename == log_file])

    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, mode="a", maxBytes=10485760, backupCount=10
        )
        # Format logs
        fmt_str = (
            "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s "
            "file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s"
        )
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # if log_level:
        if log_level is not None:
            try:
                file_handler.setLevel(log_level)
            except Exception:
                file_handler.setLevel(DEFAULT_LOG_LEVEL)

    return logger


def set_logging_configuration():
    """Set logging configuration."""
    log_file = make_splunkhome_path(
        ["var", "log", "splunk", "ta_armis_common.log"])
    file_handler = logging.handlers.RotatingFileHandler(log_file, mode="a", maxBytes=10485760, backupCount=10)
    logging.basicConfig(format="%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s"
                               " file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s", handlers=[file_handler])
