# code for logging the error or warnigns
import json
import requests
import sys
import os
import logging
import logging.handlers
import re


def setup_logger():
    logger = logging.getLogger('centurion')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.INFO)
    LOGGING_FILE_NAME = "centurion.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), maxBytes=25000000, backupCount=5)
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    return logger


# validate if input is correct ip address. only available for IPV4
def ipv4_check(value):
    regex = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''

    valid = re.search(regex, str(value))
    if valid is None:
        # raise ValueError('Invalid IP address: {0}'.format(value))
        sys.exit()

    return str(value)

