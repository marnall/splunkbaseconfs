"""this file is for logging module."""
# Standard library imports
import logging
import logging.handlers

# Splunk imports
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


def set_logging_configuration():
    """Set logging configuration."""
    log_file = make_splunkhome_path(
        ["var", "log", "splunk", "ta_vuln_db_common.log"])
    file_handler = logging.handlers.RotatingFileHandler(log_file, mode="a", maxBytes=10485760, backupCount=10)
    logging.basicConfig(format="%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s"
                               " file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s", handlers=[file_handler])
