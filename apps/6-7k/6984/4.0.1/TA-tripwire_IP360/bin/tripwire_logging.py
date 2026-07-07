import logging
import logging.config
import logging.handlers
import os

def setup_logger():

    splunk_home = os.environ.get('SPLUNK_HOME')
    log_path = os.path.join(splunk_home, 'var', 'log', 'splunk', 'tripwire_ip360.log')
    log_level = 'INFO'
    
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'sampleFormatter': {
                'format': '%(asctime)s - %(levelname)s - %(message)s'
            }
        },
        'handlers': {
            'fileHandler': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'sampleFormatter',
                'filename': log_path,
                'mode': 'a',
                'maxBytes': 100000,
                'backupCount': 5
            }
        },
        'loggers': {'tripwire_ip360': {'level': log_level, 'handlers': ['fileHandler']}},
    }
    logging.config.dictConfig(config)

