import os
import logging
import logging.config

#Akamai Enterprise Access App dir name
akamai_ea_app_dir = 'akamai_eaa'
log_path = os.getenv("SPLUNK_HOME") + '/etc/apps/' + akamai_ea_app_dir + '/logs'
#log_path = './logs'

if not os.path.exists(log_path):
    os.makedirs(log_path)
filename = log_path+"/etl.log"

#print "logging: "+filename

LOG_CONF = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(levelname)s - %(processName)s - %(process)d '
                      '- %(name)s - %(funcName)s - %(message)s',
            'datefmt': '%m/%d/%Y %I:%M:%S %p'
        },
    },
    'handlers': {
        'default': {
            'level':'INFO',
            'class':'logging.StreamHandler',
        },
        'etl': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': filename,
            'mode': 'a',
            'maxBytes': 10485760,
            'backupCount': 1
        }
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True
        },
        'etl': {
            'handlers': ['etl'],
            'level': 'INFO',
            'propagate': True
        },
        'etl-windows': {
            'handlers': ['etl'],
            'level': 'INFO',
            'propagate': True
        }
    }
}

logging.config.dictConfig(LOG_CONF)

_loggers = {}


def getLogger(name):
    if not name in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]

