import logging
import os
import sys
from logging.handlers import RotatingFileHandler

FORMATTER = logging.Formatter(
    "%(asctime)s,%(name)s,%(levelname)s,%(message)s", "%Y-%m-%d %H:%M:%S")
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
LOG_FILE = "{}/var/log/splunk/bloodhound.log".format(SPLUNK_HOME)


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler():
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=20971520, backupCount=5)
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(get_console_handler())
    logger.addHandler(get_file_handler())
    logger.propagate = False
    return logger
