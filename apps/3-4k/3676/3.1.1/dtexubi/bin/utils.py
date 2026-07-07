import os
import re
import logging
from logging.handlers import RotatingFileHandler
from json import dumps
import splunk.version as ver
import sys

APP_NAME = "dtexubi"

version = float(re.search(r"(\d+.\d+)", ver.__version__).group(1))

try:
    if version >= 6.4:
        from splunk.clilib.bundle_paths import make_splunkhome_path
    else:
        from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
except ImportError:
    sys.exit(3)


# create logger file to log error and other information
def get_logger(logger_id):
    """Return logger object."""
    log_path = make_splunkhome_path(["var", "log", APP_NAME])

    maxbytes = 2000000
    if not (os.path.isdir(log_path)):
        os.makedirs(log_path)
    file_path = os.path.join(log_path, APP_NAME + ".log")
    handler = RotatingFileHandler(file_path, maxBytes=maxbytes, backupCount=20)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger = logging.getLogger(logger_id)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


logger = get_logger("utils")


def return_object(data, status, error):
    """Return Object."""
    return dumps({"data": data, "status": status, "error": error})


def validate_zscore(zscore):
    """Validate Zscore."""
    try:
        if 1 <= int(zscore) <= 6:
            return True
        else:
            return False
    except ValueError:
        return False


def validate_threshold(threshold):
    """Validate Threshold."""
    try:
        if int(threshold) > 0:
            return True
        else:
            return False
    except ValueError:
        return False
