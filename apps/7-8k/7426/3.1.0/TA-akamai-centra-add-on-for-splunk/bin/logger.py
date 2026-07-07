# encoding = utf-8
from enum import Enum

__author__ = 'Alberto'

class LogLevel(Enum):
    """An enumeration of log levels."""

    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class Logger:
    """A class for logging messages."""

    def __init__(self, helper):
        self.helper = helper

    def log(self, level, message, *args):
        """Log a message with the specified level."""
        formatted_message = message.format(*args)
        formatted_message = "[{}] {}".format(self.helper.get_arg("name"), formatted_message)
        log_methods = {
            LogLevel.DEBUG: self.helper.log_debug,
            LogLevel.INFO: self.helper.log_info,
            LogLevel.ERROR: self.helper.log_error,
            LogLevel.CRITICAL: self.helper.log_critical
        }
        log_method = log_methods.get(level, self.helper.log_info)
        log_method(formatted_message)