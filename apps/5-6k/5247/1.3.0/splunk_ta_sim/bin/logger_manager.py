import logging
import logging.handlers
import os
from splunk.clilib.bundle_paths import make_splunkhome_path


def setup_logging(log_name, logfile_name, formatter="%(asctime)s %(levelname)s %(thread)d - %(message)s"):
    """
    @log_name: name of the logger
    @logfile_name: name of the logfile
    @level_name: log level, a string
    """

    logfile = make_splunkhome_path(["var", "log", "splunk",
                                    "%s.log" % logfile_name])
    logdir = os.path.dirname(logfile)
    if not os.path.exists(logdir):
        os.makedirs(logdir)
    logger = logging.getLogger(log_name)
    logger.propagate = False

    handler_exists = any([True for h in logger.handlers
                          if h.baseFilename == logfile])
    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(logfile, mode="a",
                                                            maxBytes=10485760,
                                                            backupCount=10)
        formatter = logging.Formatter(formatter)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger
