import logging
import os
import sys

from constants import APP_NAME

LOGGING_FORMAT = "%(levelname)-s\t%(module)s:%(lineno)d - %(message)s"


def __get_logger():
    logger = logging.getLogger(APP_NAME)
    formatter = logging.Formatter(LOGGING_FORMAT)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = __get_logger()
