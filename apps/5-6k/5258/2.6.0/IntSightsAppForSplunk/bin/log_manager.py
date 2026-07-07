import logging
import logging.handlers

from splunk.clilib.bundle_paths import make_splunkhome_path
from ta_intsights_declare import ta_lib_name


def generate_log_file_name(logger_name):
    """Generate standard log file name."""
    return "{}_{}.log".format(ta_lib_name, logger_name)


def setup_logging(logger_name, log_level=logging.INFO):
    """
    Setup Logger.

    :param logger_name: name for logger
    :param log_level: log level
    :return: logger object
    """
    file_name = generate_log_file_name(logger_name)
    log_file = make_splunkhome_path(["var", "log", "splunk", file_name])
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    logger.propagate = False

    handler_exists = any([True for h in logger.handlers if h.baseFilename == log_file])
    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, mode="a", maxBytes=10485760, backupCount=10)
        fmt_str = "%(asctime)s %(levelname)s %(thread)d - %(message)s"
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
