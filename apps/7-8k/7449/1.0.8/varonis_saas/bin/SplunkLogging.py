import os
import logging
from logging import handlers


def setup_logging(file_name):
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    LOGGING_FILE_NAME = file_name
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), maxBytes=25000000, backupCount=5)
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))

    logger = logging.getLogger('splunk.varonis')
    logger.addHandler(splunk_log_handler)
    logger.setLevel(logging.DEBUG)
    return logger
