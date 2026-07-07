__author__ = 'peter'

import logging
import os
import logging.handlers as handlers

APP = 'saas_app_akamai'


def create_logger_handler(fd, level, max_bytes=10240000, backup_count=5):
    handler = handlers.RotatingFileHandler(fd, maxBytes=max_bytes, backupCount=backup_count)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(filename)s] %(message)s'))
    handler.setLevel(level)
    return handler


def get_logger(level=logging.INFO):
    logger = logging.Logger(APP)
    log_filename = os.path.join(os.environ.get('SPLUNK_HOME'), 'var', 'log', 'splunk', '%s.log' % APP)
    logger.setLevel(level)
    handler = create_logger_handler(log_filename, level)
    logger.addHandler(handler)
    return logger

