import logging
import logging.handlers
import os

try:
    is_splunk_available = True
    from splunk.clilib.bundle_paths import make_splunkhome_path
    from splunk.clilib import cli_common as cli
except ModuleNotFoundError:
  # Running tests
    is_splunk_available = False

appname="TA-poly-Intel"
app_name="TA_poly_Intel_"
appsetting="TA_poly_Intel_setting"

DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = ('%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s')

def get_file_handler(log_file):
    """Return file handler."""
    file_handler = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=25000000, backupCount=10)
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    file_handler.setFormatter(formatter)
    return file_handler


def get_log_file_name(file_path, prefix=app_name):   
    '''Generate log file name from path.'''
    tmp_file_name = os.path.splitext(os.path.basename(file_path))[0]
    file_name = f'{prefix}{tmp_file_name}.log'
    return file_name


def get_logger(file_path=None):
    '''
    Setup Logger.   
    :param level: log level
    :return: logger object
    '''
    logger = logging.getLogger(appname)
    logger.propagate = False

    if not is_splunk_available:
        return logger

    log_level = DEFAULT_LOG_LEVEL
    logger.setLevel(log_level)

    if file_path is None:
        return logger

    file_name = get_log_file_name(file_path)
    log_file = make_splunkhome_path(['var', 'log', 'splunk', file_name])

    file_handler_exists = any(  
    [
        True
        for handler in logger.handlers
        if hasattr(handler, 'baseFilename') and handler.baseFilename == log_file
    ])
    if not file_handler_exists:
        file_handler = get_file_handler(log_file)
        logger.addHandler(file_handler)
    return logger
