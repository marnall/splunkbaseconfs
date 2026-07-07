import logging, logging.handlers
import os
import splunk
try:
    from configparser import ConfigParser
except ImportError:
    from six.moves.configparser import ConfigParser
# 0: no debug log
# 1: output error log
# 2: output warning log
# 3: output debug log
debug_map={
    "0":logging.NOTSET,
    "1":logging.ERROR,
    "2":logging.WARNING,
    "3":logging.DEBUG
}
def setup_logging():
    logger = logging.getLogger('splunk.cloud_inspector')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "cloud_inspector.log"
    BASE_LOG_PATH = os.path.join('var','log')
    LOGGING_FORMAT = "%(asctime)s [%(levelname)s] [%(process)d:%(thread)d] [%(filename)s:%(lineno)d] %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a', maxBytes=10*1024*1024, backupCount=10) 
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)

    # Get debug level
    debug_level = logging.ERROR
    try:
        INC_FILE = os.path.join(SPLUNK_HOME, 'etc', 'apps', 'cloud_inspector', 'bin', 'debug.conf')
        conf = ConfigParser()
        conf.read(INC_FILE)
        debug_str = conf.get("crs_catch", "debug_level")
        debug_level = debug_map[debug_str]
    except:
        pass
    logger.setLevel(debug_level)
    # logger.setLevel(logging.DEBUG)
    return logger
