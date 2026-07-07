# encode = utf-8

"""
This module is used to filter and reload PATH.
This file is genrated by Splunk add-on builder
"""

import os
import sys
import re
import logging
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

if sys.version_info[0] < 3:
    py_version = "aob_py3"
else:
    py_version = "aob_py3"

_APPNAME = 'TA-trellix-epo-saas-connector'

def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """

    logger = logging.getLogger('splunk.appserver.%s.controllers.controller_SPLUNK_BIN_LOG' % _APPNAME)
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(
        make_splunkhome_path(['var', 'log', 'splunk', 'trellix_saas_BIN.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.DEBUG)

logger.info("#################BEFORE###############")
ta_name = 'TA-trellix-epo-saas-connector'
ta_lib_name = 'ta_trellix_epo_saas_connector'
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name]))
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, py_version]))
sys.path = new_paths

logger.info("#################AFTER###############"+str(new_paths))