import logging
from logging import handlers
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

def setup_logger(name, debug=True):
    """
    Setup a logger.
    """

    logger = logging.getLogger(name)
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    file_handler = handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', name + '.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
