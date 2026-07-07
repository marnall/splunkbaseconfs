# Standard library imports
import logging
import logging.handlers
import os
import json

# Splunk imports
from solnlib.splunkenv import make_splunkhome_path
import splunk.rest as rest


def get_log_level(session_key):
    """
    Get configured log level.
    :param session_key: current session key of Splunk
    :return: a logging object to set level
    """
    # GET request to Logging endpoint
    conf_endpoint = "/servicesNS/nobody/{}/configs/conf-reach_security_app_for_splunk_settings/"\
        "logging".format(__file__.split(os.sep)[-3])
    _, content = rest.simpleRequest(conf_endpoint, method='GET', sessionKey=session_key, getargs={
                                    "output_mode": "json"}, raiseAllErrors=True)
    content = json.loads(content)
    content = content['entry'][0]['content']
    # Map string with Object
    mapped_log = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARN,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    return mapped_log[content['loglevel']]


def setup_logging(log_name, session_key):
    """
    Setup logger.
    :param log_name: name for logger
    :param session_key: current session key of Splunk
    :return: a logger object
    """
    # Make path till log file
    log_file = make_splunkhome_path(
        ["var", "log", "splunk", "%s.log" % log_name])
    # Get directory in which log file is present
    log_dir = os.path.dirname(log_file)
    # Create directory at the required path to store log file, if not found
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(log_name)
    logger.propagate = False

    # Get log level
    try:
        log_level = get_log_level(session_key)
    except Exception:
        # Pass if any error and set log level to default
        log_level = logging.INFO

    # Set log level
    logger.setLevel(log_level)

    handler_exists = any(
        [True for h in logger.handlers if h.baseFilename == log_file])

    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, mode="a", maxBytes=10485760, backupCount=10)
        # Format logs
        fmt_str = "%(asctime)s %(levelname)s %(thread)d - %(message)s"
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if log_level is not None:
            file_handler.setLevel(log_level)

    return logger
