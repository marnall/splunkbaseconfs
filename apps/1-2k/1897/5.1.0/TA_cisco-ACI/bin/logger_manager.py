import logging
import logging.handlers
import os

import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.clilib import cli_common as cli


APP_NAME = __file__.split(os.sep)[-3]
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = (
    "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s "
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


def get_log_file_name(file_path, prefix="ta_cisco_aci_"):
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
        cfg = cli.getConfStanza("app_setup", "logging")
        log_level = str(cfg.get("loglevel")).upper()
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


def setup_logging(log_name, log_level):
    """
    Create logger file with given file name and log level.

    :param log_name: Name of log file
    :param log_level: Log level
    :return: logger object
    """
    logfile = splunk_lib_util.make_splunkhome_path(["var", "log", "splunk", "%s.log" % log_name])
    logdir = os.path.dirname(logfile)
    if not os.path.exists(logdir):
        os.makedirs(logdir)
    logger = logging.getLogger(log_name)
    logger.propagate = False

    logger.setLevel(log_level)

    handler_exists = any([True for h in logger.handlers if h.baseFilename == logfile])
    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(logfile, mode="a", maxBytes=10485760, backupCount=10)
        fmt_str = "%(asctime)s %(levelname)s %(thread)d - %(message)s"
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        if log_level is not None:
            file_handler.setLevel(log_level)

    return logger
