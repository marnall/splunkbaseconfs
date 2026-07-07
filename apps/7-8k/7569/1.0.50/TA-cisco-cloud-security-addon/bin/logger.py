# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath, join
sys.path.append(dirname(abspath(__file__)))

import logging
from logging.handlers import RotatingFileHandler
from common import Common


class Logger(object):
    def __init__(self):
        log_file = join(Common().log_path,"TA_tos.log")
        log_format = "%(levelname)s %(asctime)s %(name)s : %(message)s"
        self.logger = logging.getLogger("TA_tos")
        self.logger.setLevel(logging.INFO)
        # create rotating file handler for error messages
        rfh = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=3)
        rfh.setLevel(logging.INFO)
        rfh.setFormatter(logging.Formatter(log_format))        
        # add the handlers to logger
        self.logger.addHandler(rfh)

    def error(self, message):
        """Log Error"""
        self.logger.error(str(message), exc_info=True)

    def info(self, message):
        """Log Info"""
        self.logger.info(str(message))
    
    def debug(self, message):
        """Log Debug"""
        self.logger.debug(str(message))
