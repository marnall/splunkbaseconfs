# Modified from splunk website
# https://dev.splunk.com/enterprise/docs/developapps/logging/loggingsplunkextensions/
#
import os
import time
import logging
import logging.handlers
import splunk

APP_NAME = 'trendmicro_cti_app'
SPLUNK_HOME = os.environ['SPLUNK_HOME']
LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
LOGGING_STANZA_NAME = 'python'
LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"


def setup_logging(log_level=logging.ERROR):
    logger = logging.getLogger(APP_NAME)

    log_filename = "{0}.log".format(APP_NAME)
    log_filepath = os.path.join(SPLUNK_HOME, 'var', 'log', APP_NAME)
    os.makedirs(log_filepath, exist_ok=True)
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_filepath, log_filename), mode='a', maxBytes=10485760,
        backupCount=10)
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.setLevel(log_level)
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE,
                             LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger
#
############################################
