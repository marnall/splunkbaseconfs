#!/usr/bin/python

import logging

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

class SplunkLogger:
    def __init__(self, app_name, log_name, level=logging.DEBUG, max_bytes=25000000, backup_count=5):
        self.logger = logging.getLogger("splunk.appserver.%s.controllers.%s" % (app_name, log_name))
        self.logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
        self.logger.setLevel(level)
        self.file_handler = logging.handlers.RotatingFileHandler(
            make_splunkhome_path(["var", "log", "splunk", "%s.log" % log_name]),
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        self.formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        self.file_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.file_handler)

    def info(self, msg):
        self.logger.info(str(msg))

    def error(self, msg):
        self.logger.error(str(msg))

class SplunkUtilityLogger:
    def __init__(self, app_name, log_name, level=logging.DEBUG, max_bytes=25000000, backup_count=5):
        self.logger = logging.getLogger("splunk.%s.bin.%s" % (app_name, log_name))
        self.logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
        self.logger.setLevel(level)
        self.file_handler = logging.handlers.RotatingFileHandler(
            make_splunkhome_path(["var", "log", "splunk", "%s.log" % log_name]),
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        self.formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        self.file_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.file_handler)

    def getSplunkUtilityLogger(self):
        return self.logger

    def info(self, msg):
        self.logger.info(str(msg))
