import logging
import logging.handlers
import os
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


def setup_logging(log_name, loglevel=logging.INFO):
    """
    To setup logger.
    
    :param log_name: name for logger
    :param loglevel: log level, a string
    :return: a logger object
    """

    logfile = make_splunkhome_path(["var", "log", "violin",
                                    "%s.log" % log_name])
    logdir = os.path.dirname(logfile)
    if not os.path.exists(logdir):
        os.makedirs(logdir)
    logger = logging.getLogger(log_name)
    logger.propagate = False
    logger.setLevel(loglevel)

    handler_exists = any([True for h in logger.handlers
                          if h.baseFilename == logfile])
    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(logfile, mode="a",
                                                            maxBytes=10485760,
                                                            backupCount=10)
        fmt_str = "%(asctime)s %(levelname)s %(thread)d - %(message)s"
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        if loglevel is not None:
            file_handler.setLevel(loglevel)

    return logger
