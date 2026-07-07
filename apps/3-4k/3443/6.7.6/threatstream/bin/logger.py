import logging
from logging import handlers

try:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
except ImportError:
    from splunk.clilib.bundle_paths import make_splunkhome_path


def setup_logger(name, log_level=logging.DEBUG, static_msg_part=""):
    """
    Setup a logger.
    """

    logger = logging.getLogger(name)
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(log_level)

    if static_msg_part != "":
        static_msg_part = static_msg_part + " "

    file_handler = handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', name + '.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(process)d %(levelname)s ' + static_msg_part + '- %(message)s')

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
