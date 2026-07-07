import sys

major_version = sys.version_info.major
if major_version == 2:
    import ConfigParser
elif major_version == 3:
    import configparser as ConfigParser

import os, logging, logging.handlers
from enum import Enum
import platform

APP_NAME = 'vision_one'

PLATFORM_STR = platform.system()

RDNS_EXPIRE_DAYS = 30
RDNS_BATCH_SIZE = 1000
RDNS_EXPIRE_SECONDS = RDNS_EXPIRE_DAYS * 24 * 60 * 60

SERVICE_ID_EXPIRE_DAYS = 30
SERVICE_ID_BATCH_SIZE = 1000
SERVICE_ID_EXPIRE_SECONDS = SERVICE_ID_EXPIRE_DAYS * 24 * 60 * 60

REPUTATION_EXPIRE_DAYS = 30
REPUTATION_BATCH_SIZE = 1000
REPUTATION_EXPIRE_SECONDS = REPUTATION_EXPIRE_DAYS * 24 * 60 * 60

QUERY_BATCH_SIZE = 500

NETWORK_TIMEOUT = 100

UPLOAD_BATCH_SIZE = 1000
DEFAULT_LAST_SEARCH_DAYS = 1
MAX_SEARCH_INTERVAL = 4 * 3600  # seconds, 4 hours
MIN_SERRCH_INTERVAL = 3600  # seconds, 1 hour


# MIN_SERRCH_INTERVAL = 300                 # 5 mins


class DestType(Enum):
    unknown = 0
    ipv4 = 1
    ipv6 = 2
    url = 3
    fqdn = 4


# 0: no debug log
# 1: output error log
# 2: output warning log
# 3: output debug log
debug_map = {
    "0": logging.NOTSET,
    "1": logging.ERROR,
    "2": logging.WARNING,
    "3": logging.DEBUG
}


def get_splunk_home():
    home = os.environ.get('SPLUNK_HOME', '')
    if not home:
        if PLATFORM_STR == "Windows":
            home = "C:\\Program Files\\Splunk"
        elif PLATFORM_STR == "Linux":
            home = "/opt/splunk"
        else:
            home = ''
    return home


def setup_logging():
    logger = logging.getLogger(APP_NAME)
    try:
        SPLUNK_HOME = os.environ['SPLUNK_HOME']
    except:
        SPLUNK_HOME = "C:\\Program Files\\Splunk"

        if PLATFORM_STR == "Windows":
            SPLUNK_HOME = "C:\\Program Files\\Splunk"
        elif PLATFORM_STR == "Linux":
            SPLUNK_HOME = "/opt/splunk"
        else:
            return None
    # SPLUNK_HOME = os.environ['SPLUNK_HOME']

    # LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    # LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    # LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "{}.log".format(APP_NAME)
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s [%(levelname)s] [%(process)d:%(thread)d] [%(filename)s:%(lineno)d] %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a', maxBytes=10 * 1024 * 1024,
        backupCount=10)
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    # splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)

    # Get debug level
    debug_level = logging.ERROR
    try:
        INC_FILE = os.path.join(SPLUNK_HOME, 'etc', 'apps', APP_NAME, 'local', 'debug.conf')
        conf = ConfigParser.ConfigParser()
        conf.read(INC_FILE)
        debug_str = conf.get("logging", "loglevel")
        debug_level = debug_map[debug_str]
    except:
        pass
    logger.setLevel(debug_level)
    # logger.setLevel(logging.DEBUG)
    return logger


class ErrorCode(Enum):
    success = 0
    # Can't access CRS server because network error
    network_error = 1
    unauthorized_access = 2
    invalid_token = 3
    too_many_request = 4
    too_many_instance = 5
    failed_parse_response = 6

    # upload error code
    upload_network_issue = 1001
    upload_invalid_token = 1002
    upload_unknown = 1003

    unknown = 9999


ERROR_STRING = {
    0: "Update success!",
    1: "Unable to update service reputation data: Backend server is unreachable, please check network or set proxy.",
    2: "Unable to update service reputation data: No permission to access backend server, please check if your email address is valid",
    3: "Unable to update service reputation data: Invalid token",
    4: "Unable to update service reputation data: Excessive requests in trial account. Contact support@trendmicro.com to increase the limit.",
    5: "Unable to update service reputation data: Reach the limit of installed instances. Contact support@trendmicro.com to increase the limit.",
    6: "Unable to update service reputation data: Unknown response from server",
    1001: "Unable to connect to the remote server. Check your proxy and internet settings and try again.",
    1002: "Invalid token detected. Copy and paste the service token from the TrendAI XDR console and try again.",
    1003: "An unexpected error has occurred. Please try again later. If the issue persists, contact your support provider.",
    9999: "Unable to update service reputation data: Unknown error"
}


class WarningCode(Enum):
    success = 0
    version_warning = 1
    invalid_upload_token = 2


WARNING_STRING = {
    0: "No Warning!",
    1: "App version (%s) is not the latest, please upgrade for better experience.",
    2: "Invalid token detected. Copy and paste the service token from the TrendAI Vision One console and try again."
}

logger = setup_logging()