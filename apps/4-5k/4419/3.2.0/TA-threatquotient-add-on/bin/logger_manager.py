# Standard library imports
import logging
import logging.handlers
import os

# Splunk imports
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from solnlib import conf_manager

addon_name = "TA-threatquotient-add-on"
conf_file_name = "ta_threatquotient_add_on_settings"


def get_log_level_from_logging_setting(session_key):
    cfm = conf_manager.ConfManager(session_key, addon_name)
    conf_dict = cfm.get_conf(conf_file_name)

    logging_stanza = conf_dict.get("logging")
    log_level = logging_stanza.get("loglevel", "INFO")

    return log_level


def setup_logging(log_name, session_key=None):
    """Logger Setup.

    :param log_name: name for logger
    :param log_level: log level, a string
    :return: a logger object
    """
    if session_key:
        log_level = get_log_level_from_logging_setting(session_key)
    else:
        log_level = "INFO"

    # Make path till log file
    log_file = make_splunkhome_path(["var", "log", "splunk", "%s.log" % log_name])
    # Get directory in which log file is present
    log_dir = os.path.dirname(log_file)
    # Create directory at the required path to store log file, if not found
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(log_name)
    logger.propagate = False

    # Set log level
    logger.setLevel(log_level)

    handler_exists = any([True for h in logger.handlers if h.baseFilename == log_file])

    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, mode="a", maxBytes=10485760, backupCount=10
        )
        # Format logs
        fmt_str = "%(asctime)s %(levelname)s %(thread)d - %(message)s"
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if log_level is not None:
            file_handler.setLevel(log_level)

    return logger


def set_logging_configuration():
    """Set logging configuration."""
    log_file = make_splunkhome_path(
        ["var", "log", "splunk", "ta_threatq_common.log"])
    file_handler = logging.handlers.RotatingFileHandler(log_file, mode="a", maxBytes=10485760, backupCount=10)
    logging.basicConfig(format="%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s"
                               " file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s", handlers=[file_handler])
