import logging
import logging.handlers
import os
import sys

import splunk

from constants import (SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME, LOGGING_FORMAT, LOGGING_DEFAULT_CONFIG_FILE,
                       LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)


def setup_logging():
    log_file_path = os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME)
    new_logger = logging.getLogger('SonarSplunk')
    new_logger.setLevel(logging.INFO)

    handler_exists = any([True for handler in new_logger.handlers if handler.baseFilename == log_file_path])

    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(log_file_path, mode='a', maxBytes=10*1024*1024, backupCount=5)
        file_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        new_logger.addHandler(file_handler)

    splunk.setupSplunkLogger(new_logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return new_logger


if sys.version_info >= (3, 0):
    string = (str, bytes)
    number = int
else:
    import __builtin__

    string = __builtin__.basestring
    number = (int, long)

logger = setup_logging()
