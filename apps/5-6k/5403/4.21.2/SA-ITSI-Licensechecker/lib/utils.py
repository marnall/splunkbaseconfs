import sys
import time
import logging
from splunk import setupSplunkLogger
from splunk.clilib.bundle_paths import make_splunkhome_path
from py3_helper import _
import py3_helper
sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'SA-ITSI-Licensechecker', 'lib', 'SA_ITSI_Licensechecker_app_common']))
sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'SA-ITSI-Licensechecker', 'lib']))
from SA_ITSI_Licensechecker_app_common.solnlib.server_info import ServerInfo
from SA_ITSI_Licensechecker_app_common.splunklib.binding import HTTPError


def setup_logging(log_file, logger_name=None, level=logging.INFO, is_console_header=False,
                  log_format='%(asctime)s %(levelname)s [%(name)s] [%(module)s] [%(funcName)s] %(message)s', is_propagate=False):
    '''
    Setup logging
    @param log_file: log file name
    @param level: logging level
    @param is_console_header: set to true if console logging is required
    @param log_format: log message format
    @param is_propagate: set to true if you want to propagate log to higher level
    @return: logger
    '''
    if log_file is None:
        raise ValueError('log_file is not specified')

    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()

    logger.propagate = is_propagate  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    # If handlers is already defined then do not create new handler, this way we can avoid file opening again
    # which is issue on windows see ITOA-2439 for more information
    if len(logger.handlers) == 0:
        file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', log_file]),
                                                            maxBytes=2500000, backupCount=5)
        file_handler.setLevel(level)
        formatter = logging.Formatter(log_format)
        file_handler.setFormatter(formatter)
        logger.handlers = []
        logger.addHandler(file_handler)

        # Console stream handler
        if is_console_header:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(logging.Formatter(log_format))
            logger.addHandler(console_handler)

    # Read logging level information from log.cfg so it will overwrite log
    # Note if logger level is specified on that file then it will overwrite log level
    LOGGING_DEFAULT_CONFIG_FILE = make_splunkhome_path(['etc', 'log.cfg'])
    LOGGING_LOCAL_CONFIG_FILE = make_splunkhome_path(['etc', 'log-local.cfg'])
    LOGGING_STANZA_NAME = 'python'
    setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME,
                      verbose=False)

    return logger


def modular_input_should_run(session_key, logger=None):
    '''
    Determine if a modular input should run or not.
    Run if and only if:
    1. Node is not a SHC member
    2. Node is an SHC member and is Captain
    @return True if condition satisfies, False otherwise
    '''
    if any([not isinstance(session_key, py3_helper.string_type), isinstance(session_key, py3_helper.string_type) and not session_key.strip()]):
        raise ValueError('Invalid session key.')

    info = ServerInfo(session_key)

    if not info.is_shc_member():
        return True

    timeout = 300  # 5 minutes
    while(timeout > 0):
        try:
            # captain election can take time on a rolling restart.
            if info.is_captain_ready():
                break
        except HTTPError as e:
            if e.status == 503:
                logger.warning('Search head cluster may be initializing on node `%s`. Captain is not ready. Try again.', info.server_name)
            else:
                logger.exception('Unexpected exception on node `%s`.', info.server_name)
                raise
        time.sleep(5)
        timeout -= 5

    # we can fairly be certain that even after 5 minutes if `is_captain_ready`
    # is false, there is a problem
    if not info.is_captain_ready():
        raise Exception('Error. Captain is not ready even after 5 minutes. node=`%s`.', info.server_name)

    return info.is_captain()
