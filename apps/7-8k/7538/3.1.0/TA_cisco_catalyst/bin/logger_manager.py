"""Log Manager for Cisco Catalyst TA."""

import os
import sys

from solnlib import log
from splunk.clilib.bundle_paths import make_splunkhome_path

DEFAULT_LOG_LEVEL = "INFO"


def get_logger(file_path=None, level="INFO"):
    """Get the logger object.

    :param file_path (string, optional): path to the logger file. Defaults to None.
    :param level (str, optional): log level to set for the logger. Defaults to "INFO".

    :return Logger object: Logger object
    """
    log_folder = make_splunkhome_path(["var", "log", "splunk", "TA_cisco_catalyst"])
    if not os.path.exists(log_folder):
        try:
            os.mkdir(log_folder)
            log.Logs.set_context(directory=log_folder, namespace="TA_cisco_catalyst")
        except Exception as e_msg:
            file_path = "TA_cisco_catalyst"
            sys.stderr.write(f"[CRITICAL] Unable to create {log_folder}: {e_msg}\n")
            sys.stderr.write(
                "logger will revert to primary TA_cisco_catalyst.log file for "
                "all message output."
            )
    else:
        log.Logs.set_context(directory=log_folder, namespace="TA_cisco_catalyst")
    logger = log.Logs().get_logger(file_path)
    try:
        logger.setLevel(level)
    except Exception:
        logger.setLevel(DEFAULT_LOG_LEVEL)
    return logger
