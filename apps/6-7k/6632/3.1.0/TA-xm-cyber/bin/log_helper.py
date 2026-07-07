"""Helper module for setting up logging in the XM Cyber Splunk app."""
import os
import logging
import import_declare_test    # noqa: F401
from import_declare_test import ta_prefix
from splunk.clilib import cli_common as cli
from splunk.clilib.bundle_paths import make_splunkhome_path

DEFAULT_LOG_LEVEL = "INFO"


def setup_logging(logger_name):
    """
    Set up Logger.

    Args:
        logger_name: name for logger

    Returns:
        logger object
    """
    # Generate log file name
    file_name = f"{logger_name}.log"
    # Make path till log file
    log_file = make_splunkhome_path(["var", "log", "splunk", file_name])
    # Get directory in which log file is present
    log_dir = os.path.dirname(log_file)
    # Create directory at the required path to store log file, if not found
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    # Get log level
    cfg = cli.getConfStanza(f'{ta_prefix.lower()}_settings', 'logging')
    log_level = str(cfg.get('loglevel'))
    # Get logger
    logger = logging.getLogger(logger_name)
    # Set log level
    try:
        logger.setLevel(log_level)
    except Exception:
        logger.setLevel(DEFAULT_LOG_LEVEL)
    logger.propagate = False

    handler_exists = False
    for h in logger.handlers:
        if h.baseFilename == log_file:
            handler_exists = True
            break
    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, mode="a", maxBytes=10485760, backupCount=10)
        # Format logs
        fmt_str = "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s"  # noqa
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if log_level:
            try:
                file_handler.setLevel(log_level)
            except Exception:
                file_handler.setLevel(DEFAULT_LOG_LEVEL)

    return logger
