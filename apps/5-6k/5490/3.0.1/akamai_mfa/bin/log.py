import logging
import logging.config
import os
from datetime import datetime, timezone
from pathlib import Path

import constants

if os.getenv(constants.splunk_home_env_variable):
    log_path = os.getenv(constants.splunk_home_env_variable) + '/etc/apps/akamai_mfa/logs'
else:
    log_path = os.path.join(Path(__file__).resolve().parent.parent, "logs")

if not os.path.exists(log_path):
    os.makedirs(log_path)
LOG_FILE = log_path + "/akamai_mfa-{}.log".format(datetime.now(timezone.utc).strftime('%Y-%m-%d'))


LOG_CONF = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(levelname)s - %(asctime)s - %(processName)s - %(process)d '
                      '- %(name)s - %(funcName)s - %(message)s',
            'datefmt': '%m/%d/%Y %I:%M:%S %p'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'akamai_mfa_log': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': LOG_FILE,
            'mode': 'a',
            'maxBytes': 10485760,
            'backupCount': 1
        }
    },

    'loggers': {
        '': {
            'handlers': ['default', 'akamai_mfa_log'],
            'level': 'INFO',
            'propagate': False
        }
    }
}


logging.config.dictConfig(LOG_CONF)

_loggers = {}


def getLogger(name):
    if not name in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]

