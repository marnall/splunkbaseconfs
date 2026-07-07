import configparser
import inspect
import logging
import logging.config
import logging.handlers
import os


def setup_logger():
    log_level = 'INFO'
    try:
        cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        cfg = configparser.ConfigParser()
        configpath = os.path.join(os.path.split(cwd)[0], 'local', 'te_setup.conf')
        cfg.read(configpath, encoding="utf-8-sig")
        if cfg.get('te_parameters', 'tripwire_debug_logging', fallback='0') == '1':
            log_level = 'DEBUG'
    except ImportError:
        pass

    splunk_home = os.environ.get('SPLUNK_HOME')
    log_path = 'tripwire.log'
    if splunk_home:
        log_path = os.path.join(splunk_home, 'var', 'log', 'splunk', 'tripwire.log')

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'detailed',
                'filename': log_path,
                'mode': 'a',
                'maxBytes': 25000000,
                'backupCount': 5,
            }
        },
        'formatters': {
            'detailed': {
                'format': (
                    '%(asctime)s %(filename)s %(process)d %(thread)d '
                    '%(levelname)s: %(message)s'
                )
            }
        },
        'loggers': {'tripwire': {'level': log_level, 'handlers': ['file']}},
    }
    logging.config.dictConfig(logging_config)
