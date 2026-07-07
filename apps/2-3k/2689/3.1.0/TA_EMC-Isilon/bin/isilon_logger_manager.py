import logging
import logging.handlers
import os
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.clilib import cli_common as cli

DEFAULT_LOG_LEVEL = "INFO"


def setup_logging(log_name, input_name=None):
    """Set logger for the given log_name."""
    custom_msg = ""
    if input_name:
        custom_msg = "input_name={} | ".format(input_name)

    log_file = make_splunkhome_path(
        ["var", "log", "splunk", "%s.log" % log_name])
    logdir = os.path.dirname(log_file)
    if not os.path.exists(logdir):
        os.makedirs(logdir)

    cfg = cli.getConfStanza('ta_emc_isilon_settings', 'logging')
    log_level = str(cfg.get('loglevel'))

    logger = logging.getLogger(log_name)
    logger.propagate = False

    try:
        logger.setLevel(log_level)
    except Exception:
        logger.setLevel(DEFAULT_LOG_LEVEL)

    handler_exists = any([True for h in logger.handlers
                          if h.baseFilename == log_file])
    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(log_file, mode="a",
                                                            maxBytes=10485760,
                                                            backupCount=10)
        fmt_str = ("%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s "
                   "file=%(filename)s:%(funcName)s:%(lineno)d | {custom_msg}%(message)s".format(custom_msg=custom_msg))
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if log_level is not None:
            try:
                file_handler.setLevel(log_level)
            except Exception:
                file_handler.setLevel(DEFAULT_LOG_LEVEL)

    return logger


def set_logging_configuration():
    """Set logging configuration."""
    log_file = make_splunkhome_path(
        ["var", "log", "splunk", "ta_emc_isilon_others.log"])
    file_handler = logging.handlers.RotatingFileHandler(log_file, mode="a", maxBytes=10485760, backupCount=10)
    logging.basicConfig(format="%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s"
                               " file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s", handlers=[file_handler])
