from types import ModuleType
from typing import Optional
import os
import logging
import logging.handlers


def setup_logging(splunk: Optional[ModuleType], log_module: str):
    logger = logging.getLogger(f"splunk.{log_module}")

    # check if SPLUNK_HOME variable set
    if os.environ.get("SPLUNK_HOME"):
        SPLUNK_HOME = os.environ["SPLUNK_HOME"]
    # else, check if Splunk present in default locations
    elif os.path.isdir("/opt/splunk"):
        SPLUNK_HOME = "/opt/splunk"
    elif os.path.isdir("/Applications/Splunk"):
        SPLUNK_HOME = "/Applications/Splunk"
    elif os.path.isdir(r"C:\Program Files\Splunk"):
        SPLUNK_HOME = r"C:\Program Files\Splunk"
    # return error, ask user to set SPLUNK_HOME
    else:
        raise Exception(
            "Splunk installation not found in default path (i.e. /opt/splunk or /Applications/splunk). Please set environment variable SPLUNK_HOME to the correct installation path."
        )
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log.cfg")
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log-local.cfg")
    LOGGING_STANZA_NAME = "python"
    LOGGING_FILE_NAME = f"splunk_{log_module}_app.log"
    BASE_LOG_PATH = os.path.join("var", "log", "splunk")
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(funcName)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME),
        mode="a",
        maxBytes=10000000,
        backupCount=10,
    )
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    if splunk:
        splunk.setupSplunkLogger(
            logger,
            LOGGING_DEFAULT_CONFIG_FILE,
            LOGGING_LOCAL_CONFIG_FILE,
            LOGGING_STANZA_NAME,
        )
    return logger
