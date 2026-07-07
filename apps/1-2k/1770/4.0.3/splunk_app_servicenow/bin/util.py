__author__ = 'strong'

import logging, os
import logging.handlers as handlers

APP = 'app_snow'


def create_logger_handler(fd, level, maxBytes=10240000, backupCount=5):
    handler = handlers.RotatingFileHandler(fd, maxBytes=maxBytes, backupCount=backupCount)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(filename)s] %(message)s'))
    handler.setLevel(level)
    return handler


def getLogger(level=logging.INFO):
    logger = logging.Logger(APP)
    LOG_FILENAME = os.path.join(os.environ.get('SPLUNK_HOME'), 'var', 'log', 'splunk', '%s.log' % APP)
    logger.setLevel(level)
    handler = create_logger_handler(LOG_FILENAME, level)
    logger.addHandler(handler)
    return logger


def flattenArgs(callerArgs, separator=','):
    args = {}
    for k in callerArgs:
        args[k] = separator.join(callerArgs[k])
    return args