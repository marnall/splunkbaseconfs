import import_declare_test  # noqa: F401
import logging
import logging.handlers

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.clilib import cli_common as cli

APP_NAME = import_declare_test.ta_name
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = (
    "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s "
    "file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s"
)


def get_file_handler(log_file):
    """Return file handler."""
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, mode="a", maxBytes=25000000, backupCount=10
    )
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    file_handler.setFormatter(formatter)
    return file_handler


def get_log_file_name(file_name):
    """Generate log file name from path."""
    return "{}.log".format(file_name)


def get_logger(file_name=None):
    """
    Return Logger.

    :param file_name: Name of the log file
    :return: logger object
    """
    # Create a logger with a unique name based on the file_name
    # This ensures each module gets its own logger instance
    if file_name:
        logger_name = f"{APP_NAME}_{file_name}"
    else:
        logger_name = APP_NAME

    logger = logging.getLogger(logger_name)
    logger.propagate = False

    # Get log level from configuration
    cfg = cli.getConfStanza("ta-cyberhaven_settings", "logging")
    log_level = str(cfg.get("loglevel")).upper()
    log_level = (
        getattr(logging, log_level)
        if hasattr(logging, log_level)
        else DEFAULT_LOG_LEVEL
    )
    logger.setLevel(log_level)

    # If no file_name provided, return the logger without file handler
    if file_name is None:
        return logger

    # Create log file path
    file_name = get_log_file_name(logger_name)
    log_file = make_splunkhome_path(["var", "log", "splunk", file_name])

    # Remove any existing handlers to prevent duplicate logging
    for handler in logger.handlers[:]:  # Use a copy of the list to safely modify during iteration
        logger.removeHandler(handler)

    # Add a new file handler
    file_handler = get_file_handler(log_file)
    logger.addHandler(file_handler)

    return logger
